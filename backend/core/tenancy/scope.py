"""Fijación transaccional del contexto de tenant (ADR-002 §2, tenancy-context §1.2–1.3).

Solo `set_config(..., true)` (equivalente a SET LOCAL): el valor muere con la transacción.
El scope raíz es DUEÑO de esa transacción (no se abre dentro de un `atomic()` ajeno), así
que al salir nunca queda contexto de BD activo detrás del ContextVar. Prohibido el SET de sesión.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import UUID

from django.db import connections, transaction

from core.tenancy.context import TenantContext, TenantContextError, _current

_GUCS = ("app.tenant_id", "app.user_id", "app.actor_type")
_SET = "SELECT " + ", ".join(f"set_config('{g}', %s, true)" for g in _GUCS)
_READ = "SELECT " + ", ".join(f"current_setting('{g}', true)" for g in _GUCS)
_user_scope_active: ContextVar[bool] = ContextVar("user_scope_active", default=False)


@contextmanager
def _owned_transaction(using: str, values: list[str]) -> Iterator[None]:
    if connections[using].in_atomic_block:
        raise TenantContextError("El scope debe ser dueño de su transacción (atomic() externo)")
    with transaction.atomic(using=using):
        with connections[using].cursor() as cursor:
            cursor.execute(_SET, values)
        yield


@contextmanager
def tenant_scope(ctx: TenantContext, *, using: str = "default") -> Iterator[TenantContext]:
    active = _current.get()
    if active is not None:
        if active != ctx:  # otro tenant, usuario o actor: nunca se mezcla
            raise TenantContextError("tenant_scope anidado con un contexto distinto")
        yield ctx  # mismo contexto completo: no-op, sin volver a fijar los GUC
        return
    if _user_scope_active.get():
        raise TenantContextError("tenant_scope no puede abrirse dentro de un user_scope")
    with _owned_transaction(
        using, [str(ctx.organization_id), str(ctx.user_id or ""), ctx.actor_type]
    ):
        token = _current.set(ctx)
        try:
            yield ctx
        finally:
            _current.reset(token)


@contextmanager
def user_scope(user_id: UUID, *, using: str = "default") -> Iterator[None]:
    """Solo `app.user_id` (sin tenant): resolver las membresías del usuario (ADR-002 §3.2)."""
    if _current.get() is not None or _user_scope_active.get():
        raise TenantContextError("user_scope no se anida ni se abre dentro de un tenant_scope")
    with _owned_transaction(using, ["", str(user_id), ""]):
        token = _user_scope_active.set(True)
        try:
            yield
        finally:
            _user_scope_active.reset(token)


def read_context(*, using: str = "default") -> tuple[str, ...]:
    with connections[using].cursor() as cursor:
        cursor.execute(_READ)
        return tuple(value or "" for value in cursor.fetchone() or ())


def assert_clean_connection(*, using: str = "default") -> None:
    """Falla (y cierra la conexión) si quedó contexto fuera de una transacción (§1.3)."""
    conn = connections[using]
    if conn.in_atomic_block:
        return
    if any(read_context(using=using)):
        conn.close()
        raise TenantContextError("La conexión conserva contexto de tenant fuera de su transacción")
