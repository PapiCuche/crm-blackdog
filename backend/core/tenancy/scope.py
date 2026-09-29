"""Fijación transaccional del contexto de tenant (ADR-002 §2, tenancy-context §1.2–1.3).

Solo `set_config(..., true)` (equivalente a SET LOCAL): el valor muere con la transacción,
así que una conexión devuelta al pool nunca conserva el tenant. Prohibido el SET de sesión.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from django.db import connections, transaction

from core.tenancy.context import TenantContext, TenantContextError, _current

_SET_CONTEXT = (
    "SELECT set_config('app.tenant_id', %s, true),"
    " set_config('app.user_id', %s, true),"
    " set_config('app.actor_type', %s, true)"
)
_READ_CONTEXT = (
    "SELECT current_setting('app.tenant_id', true), current_setting('app.user_id', true)"
)


@contextmanager
def tenant_scope(ctx: TenantContext, *, using: str = "default") -> Iterator[TenantContext]:
    active = _current.get()
    if active is not None and active.organization_id != ctx.organization_id:
        raise TenantContextError("No se puede anidar un tenant_scope de otra organización")
    with transaction.atomic(using=using):
        with connections[using].cursor() as cursor:
            cursor.execute(
                _SET_CONTEXT, [str(ctx.organization_id), str(ctx.user_id or ""), ctx.actor_type]
            )
        token = _current.set(ctx)
        try:
            yield ctx
        finally:
            _current.reset(token)


@contextmanager
def user_scope(user_id: UUID, *, using: str = "default") -> Iterator[None]:
    """Solo `app.user_id` (sin tenant): resolver las membresías del usuario (ADR-002 §3.2)."""
    if _current.get() is not None:
        raise TenantContextError("user_scope no puede usarse dentro de un tenant_scope")
    with transaction.atomic(using=using):
        with connections[using].cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.tenant_id', '', true), set_config('app.user_id', %s, true)",
                [str(user_id)],
            )
        yield


def assert_clean_connection(*, using: str = "default") -> None:
    """Falla (y cierra la conexión) si quedó contexto fuera de una transacción (§1.3)."""
    conn = connections[using]
    if conn.in_atomic_block:
        return
    with conn.cursor() as cursor:
        cursor.execute(_READ_CONTEXT)
        leftovers = [value for value in cursor.fetchone() or () if value]
    if leftovers:
        conn.close()
        raise TenantContextError("La conexión conserva contexto de tenant fuera de su transacción")
