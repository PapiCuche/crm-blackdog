"""Aislamiento de tenant contra PostgreSQL real con el rol crm_app (tenancy-context §8)."""

import re
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.db.backends.postgresql.base import DatabaseWrapper

from core.db.guards import enforce_runtime_role, runtime_role_problems
from core.tenancy.context import (
    ActorType,
    TenantContext,
    TenantContextError,
    TenantContextMissing,
)
from core.tenancy.scope import assert_clean_connection, read_context, tenant_scope, user_scope
from tests.conftest import TENANT_TABLES, migrator_settings
from tests.tenancy_app.models import Widget, WidgetPart

pytestmark = pytest.mark.usefixtures("tenant_db")


def ctx(org: UUID) -> TenantContext:
    return TenantContext(organization_id=org, source="test")


def raw_count(table: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT count(*) FROM {table}")  # noqa: S608 — nombres fijos de test
        return int(cursor.fetchone()[0])


def test_t1_without_context_sees_nothing(orgs: dict[str, UUID]) -> None:
    for table in TENANT_TABLES:
        assert raw_count(table) == 0
    with pytest.raises(TenantContextMissing):
        Widget.objects.count()


def test_t2_context_a_never_sees_b(orgs: dict[str, UUID]) -> None:
    with tenant_scope(ctx(orgs["A"])):
        assert raw_count("tenancy_app_widget") == 1  # RLS, no solo el manager
        assert list(Widget.objects.values_list("id", flat=True)) == [orgs["widget_A"]]
        assert not Widget._base_manager.filter(id=orgs["widget_B"]).exists()


def test_t3_cross_tenant_insert_is_rejected(orgs: dict[str, UUID]) -> None:
    with pytest.raises(DatabaseError), tenant_scope(ctx(orgs["A"])):
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO tenancy_app_widget (id, organization_id, name) VALUES (%s, %s, 'x')",
                [uuid4(), orgs["B"]],
            )
    with pytest.raises(TenantContextError), tenant_scope(ctx(orgs["A"])):
        Widget(organization_id=orgs["B"], name="x").save()


def test_orm_assigns_organization_from_context(orgs: dict[str, UUID]) -> None:
    with tenant_scope(ctx(orgs["A"])):
        widget = Widget.objects.create(name="nuevo")
    assert widget.organization_id == orgs["A"]


def test_composite_fk_rejects_parent_of_other_tenant(orgs: dict[str, UUID]) -> None:
    with pytest.raises(IntegrityError), tenant_scope(ctx(orgs["A"])):
        WidgetPart.objects.create(widget_id=orgs["widget_B"])  # la FK simple lo permitiría
    with tenant_scope(ctx(orgs["A"])):
        WidgetPart.objects.create(widget_id=orgs["widget_A"])


def test_t4_every_tenant_table_has_forced_rls_and_one_permissive_policy() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "JOIN pg_attribute a ON a.attrelid = c.oid "
            "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p') "
            "AND a.attname = 'organization_id'"
        )
        tables = cursor.fetchall()
        cursor.execute(
            "SELECT tablename, policyname, cmd FROM pg_policies "
            "WHERE schemaname = 'public' AND permissive = 'PERMISSIVE'"
        )
        policies = cursor.fetchall()
    assert {t for t, *_ in tables} >= set(TENANT_TABLES)
    memberships = [
        (f"memberships_{c.lower()}", c) for c in ("DELETE", "INSERT", "SELECT", "UPDATE")
    ]
    for table, rls, forced in tables:
        assert rls and forced, table
        own = sorted((name, cmd) for t, name, cmd in policies if t == table)
        # ADR-002 §3.2: única excepción, con una política por comando y sin `tenant_isolation`.
        expected = (
            memberships if table == "organization_memberships" else [("tenant_isolation", "ALL")]
        )
        assert own == expected, (table, own)


def test_t5_runtime_role_is_not_owner_superuser_or_bypassrls() -> None:
    assert runtime_role_problems(connection) == []


def test_t6_pooled_connection_never_keeps_the_tenant(orgs: dict[str, UUID]) -> None:
    with tenant_scope(ctx(orgs["A"])):
        assert raw_count("tenancy_app_widget") == 1
    assert_clean_connection()  # misma conexión (persistente), contexto ya vacío
    assert read_context() == ("", "", "")
    with tenant_scope(ctx(orgs["B"])):
        assert list(Widget.objects.values_list("id", flat=True)) == [orgs["widget_B"]]


def test_t6_session_level_leak_is_detected_and_connection_closed(orgs: dict[str, UUID]) -> None:
    session_level = "SELECT set_config('app.tenant_id', %s, " + "false)"  # simula un bug
    with connection.cursor() as cursor:
        cursor.execute(session_level, [str(orgs["A"])])
    with pytest.raises(TenantContextError):
        assert_clean_connection()
    assert connection.connection is None


def test_root_scope_sets_gucs_and_clears_them_on_exit(orgs: dict[str, UUID]) -> None:
    user = uuid4()
    root = TenantContext(orgs["A"], "test", user_id=user, actor_type=ActorType.USER)
    with tenant_scope(root):
        expected = (str(orgs["A"]), str(user), "USER")
        assert read_context() == expected
        with tenant_scope(replace(root)):  # copia idéntica (no el mismo objeto)
            assert read_context() == expected  # idéntico anidado, mismo alias: no-op
        with pytest.raises(TenantContextError), tenant_scope(root, using="otra"):
            pass  # alias sin GUC: falla antes de tocar esa conexión (ni existe)
    assert read_context() == ("", "", "")


@pytest.mark.parametrize("inner", [{"user_id": uuid4()}, {"actor_type": ActorType.AI_AGENT}])
def test_nested_scope_with_different_context_fails(orgs: dict[str, UUID], inner: Any) -> None:
    base = ctx(orgs["A"])
    for other in (replace(base, **inner), ctx(orgs["B"])):
        with pytest.raises(TenantContextError), tenant_scope(base), tenant_scope(other):
            pass
    assert read_context() == ("", "", "")


def test_scopes_must_own_their_transaction(orgs: dict[str, UUID]) -> None:
    for scope in (lambda: tenant_scope(ctx(orgs["A"])), lambda: user_scope(uuid4())):
        with pytest.raises(TenantContextError), transaction.atomic(), scope():
            pass
    assert read_context() == ("", "", "")


def test_user_scope_rules(orgs: dict[str, UUID]) -> None:
    with user_scope(uuid4()):
        assert raw_count("tenancy_app_widget") == 0  # sin tenant no se ve nada
        with pytest.raises(TenantContextError), user_scope(uuid4()):
            pass
        with pytest.raises(TenantContextError), tenant_scope(ctx(orgs["A"])):
            pass
    with pytest.raises(TenantContextError), tenant_scope(ctx(orgs["A"])), user_scope(uuid4()):
        pass
    assert read_context() == ("", "", "")


def test_t13_no_session_level_context_in_code() -> None:
    forbidden = re.compile(r"SET\s+app\.|set_config\([^)]*,\s*false\s*\)", re.IGNORECASE)
    root = Path(__file__).resolve().parents[1]
    offenders = [
        str(p.relative_to(root))
        for p in root.rglob("*.py")
        if ".venv" not in p.parts and "tests" not in p.parts and forbidden.search(p.read_text())
    ]
    assert offenders == []


def test_t16_security_definer_functions_are_hardened(orgs: dict[str, UUID]) -> None:
    migrator_role = settings.DB_MIGRATOR_ROLE
    assert migrator_role == migrator_settings()["USER"]  # el rol que migra es el propietario
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT p.oid, p.proname, coalesce(p.proconfig, '{}'), pg_get_userbyid(p.proowner), "
            "EXISTS (SELECT 1 FROM aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) a "
            "        WHERE a.grantee = 0 AND a.privilege_type = 'EXECUTE'), "
            "has_function_privilege(current_user, p.oid, 'EXECUTE') "
            "FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname = 'public' AND p.prosecdef"
        )
        functions = cursor.fetchall()
        cursor.execute("SELECT public.tenancy_widget_organization(%s)", [orgs["widget_B"]])
        assert cursor.fetchone()[0] == orgs["B"]  # lookup cross-tenant mínimo, sin tenant
    assert functions, "se esperaba al menos una función SECURITY DEFINER (app de test)"
    for _oid, name, config, owner, public_exec, app_exec in functions:
        assert any(c.startswith("search_path=") for c in config), name
        assert owner == migrator_role, name
        assert not public_exec, name
        assert app_exec, name


def test_t17_migrator_connection_is_rejected_as_runtime() -> None:
    wrapper: Any = DatabaseWrapper({**connection.settings_dict, **migrator_settings()}, "t17")
    try:
        problems = runtime_role_problems(wrapper)
        assert any("BYPASSRLS" in p for p in problems)
        assert any("propietario" in p for p in problems)
        with pytest.raises(ImproperlyConfigured):
            enforce_runtime_role(sender=None, connection=wrapper)
    finally:
        wrapper.close()


def test_migrator_fixture_can_bypass_rls_for_seeding(
    orgs: dict[str, UUID], migrator: psycopg.Connection[Any]
) -> None:
    assert migrator.execute("SELECT count(*) FROM tenancy_app_widget").fetchone() == (2,)
