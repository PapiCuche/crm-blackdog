"""Auditoría de plataforma (ADR-013): sin tenant, solo inserción e ilegible para crm_app."""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from django.core.management import call_command
from django.db import DatabaseError, connection, transaction

from apps.audit.platform import Actor, identifier_hash, record
from apps.audit.services import Entity, Result
from core.observability.context import bound
from core.tenancy.context import TenantContext, TenantContextError
from core.tenancy.scope import tenant_scope, user_scope
from tests.conftest import migrator_settings

pytestmark = pytest.mark.usefixtures("tenant_db")
SECRET = "sk-" + "ant-api03-" + "Qw7" * 30  # construido en ejecución (gitleaks sin allowlist)
EMAIL = "Ana.Owner@Example.com"
COLUMNS = (
    "actor_type, actor_id, identifier_hash, action, entity_type, entity_id, metadata::text, "
    "host(ip), user_agent, request_id, correlation_id, result"
)


def partition(months_ahead: int = 0) -> str:
    now = datetime.now(UTC)
    year, month = divmod(now.year * 12 + now.month - 1 + months_ahead, 12)
    return f"platform_audit_logs_y{year}m{month + 1:02d}"


def rows(migrator: psycopg.Connection[Any], columns: str = COLUMNS) -> list[tuple[Any, ...]]:
    return migrator.execute(f"SELECT {columns} FROM platform_audit_logs").fetchall()  # noqa: S608


def test_failed_login_keeps_a_hash_and_never_the_identifier(
    migrator: psycopg.Connection[Any],
) -> None:
    with bound(request_id="req-1", correlation_id="corr-1"):
        audit_id = record(
            "auth.login.failed",
            actor_type=Actor.ANONYMOUS,
            identifier=EMAIL,
            metadata={
                "reason": "unknown_identifier",
                "password": "hunter2",
                "note": SECRET,
                "detail": f"intento de {EMAIL} desde otra red",
                "session_key": "abc123sessionkey",
                "session_id": "abc123sessionid",
                "csrftoken": "tok-csrf-1",
                "X-CSRFToken": "tok-csrf-2",
            },
            result=Result.FAILED,
            ip="203.0.113.7",
            user_agent=f"Mozilla/5.0 ({EMAIL}) " + "x" * 600,
        )
    (row,) = rows(migrator)
    assert row[:6] == ("ANONYMOUS", None, identifier_hash(EMAIL), "auth.login.failed", None, None)
    assert json.loads(row[6]) == {
        "reason": "unknown_identifier",
        "password": "[REDACTED]",
        "note": "[REDACTED]",
        "detail": "intento de [EMAIL] desde otra red",
        "session_key": "[REDACTED]",
        "session_id": "[REDACTED]",
        "csrftoken": "[REDACTED]",
        "X-CSRFToken": "[REDACTED]",
    }
    assert row[7] == "203.0.113.7" and len(row[8]) == 512 and "[EMAIL]" in row[8]
    assert row[9:] == ("req-1", "corr-1", "FAILED")
    whole = migrator.execute("SELECT t::text FROM platform_audit_logs t").fetchone()
    assert whole is not None and str(audit_id) in whole[0]
    for forbidden in (EMAIL, EMAIL.lower(), "example.com", "hunter2", SECRET, "abc123", "tok-csrf"):
        assert forbidden not in whole[0]


def test_identifier_hash_is_keyed_and_normalized(settings: Any) -> None:
    digest = identifier_hash(EMAIL)
    assert len(digest) == 64 and digest == identifier_hash("  " + EMAIL.lower() + " ")
    assert digest != identifier_hash("otra@example.com")
    settings.SECRET_KEY = "otra-clave-" + "k" * 40
    assert identifier_hash(EMAIL) != digest  # sin la clave no se puede recalcular


def test_failed_login_names_the_targeted_account_as_entity(
    migrator: psycopg.Connection[Any],
) -> None:
    account = uuid4()  # la cuenta atacada no es el actor: nadie se ha autenticado (ADR-013 §4)
    record(
        "auth.login.failed",
        actor_type=Actor.ANONYMOUS,
        identifier=EMAIL,
        entity=Entity("user", account),
        result=Result.FAILED,
    )
    (row,) = rows(migrator)
    assert row[:6] == (
        "ANONYMOUS", None, identifier_hash(EMAIL), "auth.login.failed", "user", account
    )  # fmt: skip


def test_user_event_with_entity_and_ipv6(migrator: psycopg.Connection[Any]) -> None:
    user, org = uuid4(), uuid4()
    record(
        "organization.bootstrapped",
        actor_type=Actor.PLATFORM_STAFF,
        actor_id=user,
        entity=Entity("organization", org),
        metadata={"reason": "alta inicial"},
        ip="2001:db8::1",
    )
    (row,) = rows(migrator)
    assert row[:6] == (
        "PLATFORM_STAFF",
        user,
        None,
        "organization.bootstrapped",
        "organization",
        org,
    )
    assert (row[7], row[8], row[9], row[10], row[11]) == (
        "2001:db8::1",
        None,
        None,
        None,
        "SUCCESS",
    )


def test_record_rejects_a_tenant_scope_and_invalid_input(
    orgs: dict[str, UUID], migrator: psycopg.Connection[Any]
) -> None:
    with tenant_scope(TenantContext(orgs["A"], "test")), pytest.raises(TenantContextError):
        record("auth.logout", actor_type=Actor.SYSTEM)
    cases: tuple[dict[str, Any], ...] = (
        {"action": "Auth.Logout", "actor_type": Actor.SYSTEM},
        {"action": "logout", "actor_type": Actor.SYSTEM},
        {"action": "auth.logout", "actor_type": "ROBOT"},
        {"action": "auth.logout", "actor_type": Actor.ANONYMOUS, "actor_id": uuid4()},
        {"action": "auth.logout", "actor_type": Actor.SYSTEM, "ip": "no-es-una-ip"},
        {"action": "auth.logout", "actor_type": Actor.SYSTEM, "ip": "10.0.0.1, 10.0.0.2"},
        {"action": "auth.logout", "actor_type": Actor.SYSTEM, "entity": Entity("Organization")},
        {"action": "auth.logout", "actor_type": Actor.SYSTEM, "result": "MAYBE"},
        {"action": "auth.logout", "actor_type": Actor.SYSTEM, "metadata": {"blob": "x" * 5000}},
    )
    for kwargs in cases:
        with pytest.raises(ValueError):
            record(kwargs.pop("action"), **kwargs)
    assert rows(migrator) == []


def test_record_works_inside_a_user_scope_and_follows_the_transaction(
    migrator: psycopg.Connection[Any],
) -> None:
    user = uuid4()
    with user_scope(user):  # rutas de plataforma que listan las membresías del usuario
        record("auth.login.succeeded", actor_type=Actor.USER, actor_id=user)
    with pytest.raises(RuntimeError), transaction.atomic():
        record("auth.logout", actor_type=Actor.USER, actor_id=user)
        raise RuntimeError("la operación auditada falla")
    assert [r[3] for r in rows(migrator)] == ["auth.login.succeeded"]  # el rollback se lo lleva


@pytest.mark.parametrize(
    "statement",
    [
        "SELECT count(*) FROM platform_audit_logs",
        "UPDATE platform_audit_logs SET action = 'x.y'",
        "DELETE FROM platform_audit_logs",
        "TRUNCATE platform_audit_logs",
        "INSERT INTO platform_audit_logs (actor_type, action) VALUES ('SYSTEM', 'x.y') "
        "RETURNING id",
        "SELECT count(*) FROM {partition}",
        "UPDATE {partition} SET action = 'x.y'",
        "DELETE FROM {partition}",
        "INSERT INTO {partition} (actor_type, action) VALUES ('SYSTEM', 'x.y')",
    ],
)
def test_crm_app_can_only_insert(migrator: psycopg.Connection[Any], statement: str) -> None:
    record("auth.logout", actor_type=Actor.SYSTEM)
    with pytest.raises(DatabaseError, match="permission denied"), connection.cursor() as cursor:
        cursor.execute(statement.format(partition=partition()))
    assert rows(migrator, "count(*), min(action)") == [(1, "auth.logout")]  # evidencia intacta


def test_privileges_partitions_and_no_tenant_column(migrator: psycopg.Connection[Any]) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT p FROM unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE',"
            "'REFERENCES','TRIGGER']) p "
            "WHERE has_table_privilege(current_user, 'platform_audit_logs', p)"
        )
        assert [r[0] for r in cursor.fetchall()] == ["INSERT"]
        cursor.execute(
            "SELECT c.relname, has_table_privilege(current_user, c.oid, "
            "'SELECT,INSERT,UPDATE,DELETE,TRUNCATE') FROM pg_inherits i JOIN pg_class c "
            "ON c.oid = i.inhrelid WHERE i.inhparent = 'platform_audit_logs'::regclass"
        )
        partitions = dict(cursor.fetchall())
        cursor.execute(
            "SELECT has_function_privilege('platform_audit_ensure_partitions(integer)', 'EXECUTE')"
        )
        assert cursor.fetchone() == (False,)  # crm_app no crea particiones (sin DDL)
        cursor.execute(
            "SELECT count(*) FROM pg_attribute WHERE attrelid = 'platform_audit_logs'::regclass "
            "AND attname = 'organization_id'"
        )
        assert cursor.fetchone() == (0,)  # platform-owned: sin tenant (ADR-001 §2)
    assert not any(partitions.values())  # ningún privilegio directo sobre particiones
    assert {partition(k) for k in range(13)} <= set(partitions)  # mes actual + 12
    owner = migrator.execute(
        "SELECT pg_get_userbyid(relowner), relrowsecurity FROM pg_class "
        "WHERE oid = 'platform_audit_logs'::regclass"
    ).fetchone()
    assert owner == ("crm_migrator", False)


def test_post_migrate_restores_the_partition_horizon(migrator: psycopg.Connection[Any]) -> None:
    migrator.execute(f"DROP TABLE {partition(12)}")  # simula un año sin desplegar
    runtime = dict(connection.settings_dict)
    connection.close()
    connection.settings_dict.update(migrator_settings())
    try:
        call_command("migrate", verbosity=0)  # post_migrate → platform_audit_ensure_partitions
    finally:
        connection.close()
        connection.settings_dict.clear()
        connection.settings_dict.update(runtime)
    exists = migrator.execute("SELECT to_regclass(%s) IS NOT NULL", [partition(12)]).fetchone()
    assert exists == (True,)
