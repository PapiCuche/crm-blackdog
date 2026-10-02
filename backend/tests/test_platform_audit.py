"""Auditoría de plataforma (ADR-013): sin tenant, solo inserción e ilegible para crm_app."""

import json
import time
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from django.core.management import call_command
from django.db import DatabaseError, connection, transaction

from apps.audit import platform
from apps.audit.platform import Actor, identifier_hash, record
from apps.audit.services import Entity, Result
from core.observability.context import bound
from core.tenancy.context import TenantContext, TenantContextError
from core.tenancy.scope import tenant_scope, user_scope
from tests.conftest import migrator_conninfo, migrator_settings

pytestmark = pytest.mark.usefixtures("tenant_db")
SECRET = "sk-" + "ant-api03-" + "Qw7" * 30  # construido en ejecución (gitleaks sin allowlist)
EMAIL = "Ana.Owner@Example.com"
COLUMNS = (
    "actor_type, actor_id, identifier_hash, action, entity_type, entity_id, metadata::text, "
    "host(ip), user_agent, request_id, correlation_id, result"
)
ADDRESSES = [
    "josé@example.com",
    "josé@example.com",  # la misma dirección en forma NFD
    "begoña.nuñez@example.com",
    "maria@españa.es",
    "пользователь@пример.рф",
    "root@localhost",
    "user@[10.0.0.1]",
    "o'brien@example.com",
    "ana%40example.com",
]
DIRECT = [  # lo que el servicio rechaza, enviado directamente a la tabla
    "INSERT INTO platform_audit_logs (actor_type, action, actor_id) "
    "VALUES ('ANONYMOUS', 'auth.login.failed', uuidv7())",
    "INSERT INTO platform_audit_logs (actor_type, action) VALUES ('SYSTEM', 'No es una acción')",
    "INSERT INTO platform_audit_logs (actor_type, action, metadata) "
    "VALUES ('SYSTEM', 'auth.logout', jsonb_build_object('k', repeat('x', 9000)))",
]


def partition(months_ahead: int = 0) -> str:
    """El nombre sale del reloj de la BD, como en la función que crea las particiones."""
    with psycopg.connect(migrator_conninfo(), autocommit=True) as conn:
        row = conn.execute(
            "SELECT to_char(date_trunc('month', now() AT TIME ZONE 'UTC') "
            '+ make_interval(months => %s), \'"platform_audit_logs_y"YYYY"m"MM\')',
            [months_ahead],
        ).fetchone()
    assert row is not None
    return str(row[0])


def rows(migrator: psycopg.Connection[Any], columns: str = COLUMNS) -> list[tuple[Any, ...]]:
    order = "" if "count(" in columns else " ORDER BY occurred_at, id"
    query = f"SELECT {columns} FROM platform_audit_logs{order}"  # noqa: S608
    return migrator.execute(query).fetchall()


def whole(migrator: psycopg.Connection[Any]) -> str:
    """Todas las filas, como texto: lo que vería quien leyera la tabla."""
    found = migrator.execute("SELECT t::text FROM platform_audit_logs t").fetchall()
    return "\n".join(row[0] for row in found)


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
            user_agent=f"Mozilla/5.0 ({EMAIL}) {SECRET} " + "x" * 600,
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
    assert row[7] == "203.0.113.7" and len(row[8]) == 512
    assert row[8].startswith("Mozilla/5.0 ([EMAIL]) [REDACTED] x")
    assert row[9:] == ("req-1", "corr-1", "FAILED")
    text = whole(migrator)
    assert str(audit_id) in text
    for forbidden in (EMAIL, EMAIL.lower(), "example.com", "hunter2", SECRET, "abc123", "tok-csrf"):
        assert forbidden not in text


@pytest.mark.parametrize("address", ADDRESSES)
def test_no_email_shaped_string_is_stored_anywhere(
    migrator: psycopg.Connection[Any], address: str
) -> None:
    record(
        "auth.login.failed",
        actor_type=Actor.ANONYMOUS,
        metadata={"detail": f"de {address}.", "to": [address], "ctx": {"who": address}, address: 1},
        user_agent=f"agente peña {address} fin",
        result=Result.FAILED,
    )
    text = whole(migrator)
    local, domain = address.replace("%40", "@").split("@")
    assert address not in text and local not in text and domain not in text
    assert text.count("[EMAIL]") >= 5  # valor, lista, anidado, clave y agente de usuario


def test_session_and_csrf_values_never_reach_the_row(migrator: psycopg.Connection[Any]) -> None:
    record(
        "auth.logout",
        actor_type=Actor.SYSTEM,
        metadata={
            "detail": "Cookie: __Host-crm_session=LEAK01; sessionid=LEAK02",
            "note": "session_key=LEAK03 y X-CSRFToken: LEAK04",
            "__Host-crm_session": "LEAK05",
            "repr": "{'sessionid': 'LEAK06'}",
        },
        user_agent="curl/8 Cookie: crm_session=LEAK07",
    )
    assert "LEAK" not in whole(migrator)


def test_hostile_text_costs_linear_time_and_is_bounded(migrator: psycopg.Connection[Any]) -> None:
    started = time.perf_counter()
    for agent in ("." * 16000, "a" * 16000, "a@" + "a." * 8000, "\x00" + "x" * 600):
        record("auth.login.failed", actor_type=Actor.ANONYMOUS, user_agent=agent)
    for huge in ("." * 40000, "a@" + "a." * 20000):
        with pytest.raises(ValueError, match="metadata supera"):
            record("auth.logout", actor_type=Actor.SYSTEM, metadata={"k": huge})
    assert time.perf_counter() - started < 2  # con las expresiones anteriores: segundos por llamada
    agents = [row[0] for row in rows(migrator, "user_agent")]
    assert len(agents) == 4 and all(len(agent) <= 512 for agent in agents)
    assert "\\0" not in whole(migrator)


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


def test_platform_event_with_entity_and_normalized_address(
    migrator: psycopg.Connection[Any],
) -> None:
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
        "PLATFORM_STAFF", user, None, "organization.bootstrapped", "organization", org
    )  # fmt: skip
    assert row[7:] == ("2001:db8::1", None, None, None, "SUCCESS")
    for given, stored in (("fe80::1%eth0", "fe80::1"), ("::ffff:203.0.113.9", "203.0.113.9")):
        record("auth.logout", actor_type=Actor.SYSTEM, ip=given)  # sin zona ni IPv4-en-IPv6
        assert rows(migrator, "host(ip)")[-1] == (stored,)
    record("auth.logout", actor_type=Actor.SYSTEM, identifier="   ")
    assert rows(migrator, "identifier_hash")[-1] == (None,)  # un identificador vacío no cuenta


def test_record_rejects_a_tenant_scope_and_invalid_input(
    orgs: dict[str, UUID], migrator: psycopg.Connection[Any]
) -> None:
    with tenant_scope(TenantContext(orgs["A"], "test")), pytest.raises(TenantContextError):
        record("auth.logout", actor_type=Actor.SYSTEM)
    logout: dict[str, Any] = {"action": "auth.logout", "actor_type": Actor.SYSTEM}
    cases: tuple[dict[str, Any], ...] = (
        {"action": "Auth.Logout", "actor_type": Actor.SYSTEM},
        {"action": "logout", "actor_type": Actor.SYSTEM},
        {"action": "auth." + "x" * 100, "actor_type": Actor.SYSTEM},
        {"action": "auth.logout", "actor_type": "ROBOT"},
        {"action": "auth.logout", "actor_type": Actor.ANONYMOUS, "actor_id": uuid4()},
        {"action": "auth.login.succeeded", "actor_type": Actor.USER},  # USER sin actor_id
        {**logout, "ip": "no-es-una-ip"},
        {**logout, "ip": "10.0.0.1, 10.0.0.2"},
        {**logout, "ip": 2130706433},
        {**logout, "entity": Entity("Organization")},
        {**logout, "result": "MAYBE"},
        {**logout, "metadata": {"blob": "x" * 5000}},
        {**logout, "metadata": {"n": float("nan")}},
        {**logout, "metadata": {"n": "a\x00b"}},
        {**logout, "metadata": {EMAIL: 1, "x@y.z": 2}},  # dos claves no se funden en una
    )
    for kwargs in cases:
        with pytest.raises(ValueError):
            record(kwargs.pop("action"), **kwargs)
    with pytest.raises(TypeError):  # no hay forma de pasarle un tenant
        record("auth.logout", actor_type=Actor.SYSTEM, organization_id=orgs["A"])  # type: ignore[call-arg]
    assert rows(migrator) == []


def test_a_failed_insert_raises_and_leaves_the_caller_transaction_usable(
    migrator: psycopg.Connection[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    record("auth.logout", actor_type=Actor.SYSTEM)
    beyond = platform._INSERT.replace("now()", "now() + interval '20 months'", 1)
    monkeypatch.setattr(platform, "_INSERT", beyond)  # fuera del horizonte: sin partición
    with pytest.raises(DatabaseError, match="no partition of relation"):
        record("auth.login.succeeded", actor_type=Actor.USER, actor_id=uuid4())  # falla cerrado
    with pytest.raises(DatabaseError), transaction.atomic():
        record("auth.login.succeeded", actor_type=Actor.USER, actor_id=uuid4())
        pytest.fail("la operación auditada no debe continuar")
    user = uuid4()
    with user_scope(user), connection.cursor() as cursor:
        cursor.execute("DELETE FROM django_session")  # quien captura el error (logout, §5)…
        with pytest.raises(DatabaseError):
            record("auth.logout", actor_type=Actor.USER, actor_id=user)
        cursor.execute("SELECT 1")  # …conserva su transacción
        assert cursor.fetchone() == (1,)
    assert rows(migrator, "action") == [("auth.logout",)]  # solo la fila anterior


def test_a_temporary_table_cannot_capture_the_audit(migrator: psycopg.Connection[Any]) -> None:
    with connection.cursor() as cursor:  # crm_app puede crear tablas temporales
        cursor.execute(
            "CREATE TEMP TABLE platform_audit_logs (id uuid, occurred_at timestamptz, "
            "actor_type text, actor_id uuid, identifier_hash text, action text, entity_type text, "
            "entity_id uuid, metadata jsonb, ip inet, user_agent text, request_id text, "
            "correlation_id text, result text)"
        )
    try:
        audit_id = record("auth.logout", actor_type=Actor.SYSTEM)
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM pg_temp.platform_audit_logs")
            assert cursor.fetchone() == (0,)
    finally:
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE pg_temp.platform_audit_logs")
    assert rows(migrator, "id") == [(audit_id,)]


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


@pytest.mark.parametrize("statement", DIRECT)
def test_the_table_itself_rejects_what_the_service_rejects(
    migrator: psycopg.Connection[Any], statement: str
) -> None:
    with pytest.raises(DatabaseError, match="check constraint"), connection.cursor() as cursor:
        cursor.execute(statement)  # un runtime comprometido tampoco puede saltarse las reglas
    assert rows(migrator) == []


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
    table = migrator.execute(
        "SELECT pg_get_userbyid(c.relowner), c.relrowsecurity, p.partdefid FROM pg_class c "
        "JOIN pg_partitioned_table p ON p.partrelid = c.oid "
        "WHERE c.oid = 'platform_audit_logs'::regclass"
    ).fetchone()
    assert table == ("crm_migrator", False, 0)  # sin partición DEFAULT: fuera del horizonte, falla


def test_post_migrate_restores_the_horizon_and_repairs_privileges(
    migrator: psycopg.Connection[Any],
) -> None:
    migrator.execute(f"DROP TABLE {partition(12)}")  # simula un año sin desplegar
    stray = partition(20)  # partición hecha a mano: hereda los privilegios por defecto
    migrator.execute(
        f"CREATE TABLE {stray} PARTITION OF platform_audit_logs "
        "FOR VALUES FROM (date_trunc('month', now()) + interval '20 months') "
        "TO (date_trunc('month', now()) + interval '21 months')"
    )
    migrator.execute("GRANT SELECT, DELETE ON platform_audit_logs TO crm_app")  # privilegio de más
    runtime = dict(connection.settings_dict)
    connection.close()
    connection.settings_dict.update(migrator_settings())
    try:
        call_command("migrate", verbosity=0)  # post_migrate → platform_audit_ensure_partitions
    finally:
        connection.close()
        connection.settings_dict.clear()
        connection.settings_dict.update(runtime)
    try:
        exists = migrator.execute("SELECT to_regclass(%s) IS NOT NULL", [partition(12)]).fetchone()
        assert exists == (True,)
        with connection.cursor() as cursor:  # el deploy repara los privilegios, no solo crea
            cursor.execute(
                "SELECT has_table_privilege(current_user, %s, 'SELECT,INSERT,UPDATE,DELETE'), "
                "has_table_privilege(current_user, 'platform_audit_logs', 'SELECT,UPDATE,DELETE'),"
                " has_table_privilege(current_user, 'platform_audit_logs', 'INSERT')",
                [stray],
            )
            assert cursor.fetchone() == (False, False, True)
    finally:
        migrator.execute(f"DROP TABLE {stray}")
