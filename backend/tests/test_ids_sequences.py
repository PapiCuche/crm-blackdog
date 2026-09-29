"""UUIDv7 y numeración comercial por organización (ADR-004) contra PostgreSQL real."""

import threading
import time
from uuid import UUID

import psycopg
import pytest
from django.apps import apps
from django.db import IntegrityError, connection, models, transaction

from apps.organizations.models import Organization
from core.ids import new_id
from core.models import OrgSequence
from core.sequences import allocate, format_number
from core.tenancy.context import TenantContext, TenantContextError
from core.tenancy.scope import tenant_scope

pytestmark = pytest.mark.usefixtures("tenant_db")


def ctx(org: UUID) -> TenantContext:
    return TenantContext(organization_id=org, source="test")


def number(formatted: str) -> int:
    return int(formatted.rsplit("-", 1)[1])


class Rollback(Exception):
    pass


def test_new_id_is_uuidv7_and_time_ordered() -> None:
    ids = [new_id() for _ in range(1000)]
    assert {i.version for i in ids} == {7}
    assert ids == sorted(ids) and len(set(ids)) == len(ids)  # monótonos: índices B-tree


def test_database_default_is_uuidv7(orgs: dict[str, UUID]) -> None:
    with connection.cursor() as cursor:  # INSERT SQL directo como crm_app, sin id
        cursor.execute(
            "INSERT INTO organizations (slug, name, status, created_at) "
            "VALUES ('sql-directo', 'SQL', 'ACTIVE', now()) RETURNING id"
        )
        (created,) = cursor.fetchone()
    assert UUID(str(created)).version == 7
    assert Organization.objects.create(slug="orm", name="ORM").id.version == 7  # new_id()


def test_sequences_reference_an_existing_organization() -> None:
    ghost = ctx(new_id())  # organización inexistente (FK org_sequences_organization_fk)
    with pytest.raises(IntegrityError), tenant_scope(ghost):
        allocate(ghost, "COT")


def test_kernel_and_app_primary_keys_are_uuidv7() -> None:
    """ADR-004 §1: toda PK de core/apps es UUIDv7 (`uuid7_primary_key`) o compuesta."""
    for model in apps.get_models():
        if model.__module__.startswith(("core.", "apps.")):
            pk = model._meta.pk
            composite = isinstance(pk, models.CompositePrimaryKey)
            assert composite or getattr(pk, "default", None) is new_id, model


def test_allocate_requires_atomic_and_the_active_tenant(orgs: dict[str, UUID]) -> None:
    with pytest.raises(TenantContextError, match="atomic"):
        allocate(ctx(orgs["A"]), "COT")
    with pytest.raises(TenantContextError, match="tenant_scope"), transaction.atomic():
        allocate(ctx(orgs["A"]), "COT")  # atomic sin tenant
    with pytest.raises(TenantContextError, match="tenant_scope"), tenant_scope(ctx(orgs["A"])):
        allocate(ctx(orgs["B"]), "COT")  # otra organización
    for key in ("cot", "", "C-1", "X" * 17, "COT\n", "X" * 16 + "\n"):
        with pytest.raises(ValueError), tenant_scope(ctx(orgs["A"])):
            allocate(ctx(orgs["A"]), key)


def test_allocate_is_sequential_per_organization_and_key(orgs: dict[str, UUID]) -> None:
    with tenant_scope(ctx(orgs["A"])):
        got = [allocate(ctx(orgs["A"]), "COT") for _ in range(2)]
        got += [allocate(ctx(orgs["A"]), "OPP"), allocate(ctx(orgs["A"]), "COT", prefix="Q")]
    assert got == ["COT-000001", "COT-000002", "OPP-000001", "Q-000003"]
    with tenant_scope(ctx(orgs["B"])):
        assert allocate(ctx(orgs["B"]), "COT") == "COT-000001"  # independiente por tenant
        assert OrgSequence.objects.count() == 1
        with connection.cursor() as cursor:  # SQL raw: RLS, no solo el manager
            cursor.execute("SELECT count(*) FROM org_sequences")
            assert cursor.fetchone() == (1,)  # las 2 claves de A son invisibles
    assert format_number("COT", 1_000_000) == "COT-1000000"  # crece sin romper nada


def test_rollback_does_not_consume_a_number(orgs: dict[str, UUID]) -> None:
    a = ctx(orgs["A"])
    with tenant_scope(a):
        assert allocate(a, "COT") == "COT-000001"
    with pytest.raises(Rollback), tenant_scope(a):
        allocate(a, "COT")
        raise Rollback
    with tenant_scope(a):
        with pytest.raises(Rollback), transaction.atomic():  # savepoint
            allocate(a, "COT")
            raise Rollback
        assert allocate(a, "COT") == "COT-000002"  # sin huecos


def test_concurrent_allocation_is_unique_and_gapless(
    orgs: dict[str, UUID], migrator: psycopg.Connection[object]
) -> None:
    threads_per_org, rounds = 8, 10
    committed: dict[str, list[int]] = {"A": [], "B": []}
    errors: list[BaseException] = []
    start = threading.Barrier(threads_per_org * 2, timeout=30)
    lock = threading.Lock()

    def worker(org: str, seed: int) -> None:
        tenant = ctx(orgs[org])
        try:
            start.wait()
            for i in range(rounds):
                try:
                    with tenant_scope(tenant):
                        value = number(allocate(tenant, "COT"))
                        time.sleep(0.002)  # retiene el bloqueo de fila: fuerza la contención
                        if (seed + i) % 3 == 0:
                            raise Rollback  # rollback: el número se reutiliza
                except Rollback:
                    continue
                with lock:
                    committed[org].append(value)
        except BaseException as exc:  # noqa: BLE001 — se re-lanza en el hilo principal
            errors.append(exc)
        finally:
            connection.close()  # conexión propia de cada hilo

    threads = [
        threading.Thread(target=worker, args=(org, n), daemon=True)
        for org in ("A", "B")
        for n in range(threads_per_org)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert not errors, errors
    assert not any(t.is_alive() for t in threads), "hilo bloqueado"
    expected = sum(1 for n in range(threads_per_org) for i in range(rounds) if (n + i) % 3)
    for org in ("A", "B"):
        values = committed[org]
        assert len(values) == expected, org  # cada commit asignó un número
        assert sorted(values) == list(range(1, expected + 1)), org  # únicos y sin huecos
        row = migrator.execute(
            "SELECT next_value FROM org_sequences "
            "WHERE organization_id = %s AND sequence_key = 'COT'",
            [orgs[org]],
        ).fetchone()
        assert row == (len(values) + 1,)
