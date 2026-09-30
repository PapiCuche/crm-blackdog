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
_active_using: ContextVar[str | None] = ContextVar("tenant_scope_using", default=None)


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
        if active != ctx or _active_using.get() != using:  # otra conexión no tiene los GUC
            raise TenantContextError("tenant_scope anidado con otro contexto o alias de conexión")
        yield ctx  # mismo contexto y alias: no-op, sin volver a fijar los GUC
        return
    if _user_scope_active.get():
        raise TenantContextError("tenant_scope no puede abrirse dentro de un user_scope")
    with _owned_transaction(
        using, [str(ctx.organization_id), str(ctx.user_id or ""), ctx.actor_type]
    ):
        token, alias_token = _current.set(ctx), _active_using.set(using)
        try:
            yield ctx
        finally:
            _current.reset(token)
            _active_using.reset(alias_token)


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


def require_scope(ctx: TenantContext) -> str:
    """Alias del `tenant_scope` activo si es exactamente `ctx` y su transacción sigue abierta.

    Las APIs que escriben en nombre del tenant (outbox, auditoría) lo usan en lugar de recibir
    `using`: así nunca escriben en una conexión sin los GUC del scope (OBS-F1-05-2).
    """
    alias = _active_using.get()
    if alias is None or _current.get() != ctx or not connections[alias].in_atomic_block:
        raise TenantContextError("Se requiere el tenant_scope activo de este mismo contexto")
    return alias


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
