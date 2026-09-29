"""Contexto de tenant (docs/architecture/tenancy-context.md §1.1)."""

from contextvars import ContextVar
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class ActorType(StrEnum):
    USER = "USER"
    AI_AGENT = "AI_AGENT"
    SYSTEM = "SYSTEM"
    INTEGRATION = "INTEGRATION"


class TenantContextError(RuntimeError):
    """Uso incorrecto del contexto de tenant (anidar tenants distintos, fuga de conexión…)."""


class TenantContextMissing(TenantContextError):
    """Acceso a datos tenant-owned sin `tenant_scope` activo."""


@dataclass(frozen=True, slots=True)
class TenantContext:
    organization_id: UUID
    source: str
    user_id: UUID | None = None
    actor_type: ActorType = ActorType.SYSTEM
    actor_id: UUID | None = None
    correlation_id: str | None = None


_current: ContextVar[TenantContext | None] = ContextVar("tenant_context", default=None)


def current() -> TenantContext | None:
    return _current.get()


def require() -> TenantContext:
    ctx = _current.get()
    if ctx is None:
        raise TenantContextMissing("Se requiere tenant_scope() para acceder a datos de tenant")
    return ctx
