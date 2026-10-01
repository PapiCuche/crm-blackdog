"""El motor de autorización en DRF (ADR-003 §5, frontera B2). Denegación por defecto.

`HasPermission` y `ScopeFilter` son los valores por defecto de DRF (`config.settings.base`).
Una vista de tenant declara el permiso de cada método en `required_permissions`; vista sin
declaración, método sin declarar o petición sin contexto de tenant: denegado.

El contexto es el que resolvió el middleware (`core.tenancy.context`), nunca `request.user`
ni datos del cliente. Las vistas de plataforma son las rutas fuera de `/api/v1/o/<slug>/`:
otra frontera, con sus propias `permission_classes` y `filter_backends`. Se excluyen por la
ruta, no por el actor: ser staff de plataforma no abre ninguna ruta de tenant.
"""

from collections.abc import Mapping
from typing import Any

from django.db.models import Model, QuerySet
from rest_framework.exceptions import NotFound
from rest_framework.filters import BaseFilterBackend
from rest_framework.permissions import BasePermission

from apps.access.selectors import (
    AccessDenied,
    ExecutionContext,
    can,
    execution_context,
    has_permission,
    scoped,
)
from core.tenancy import context


def required_code(request: Any, view: Any) -> str | None:
    """Permiso que la vista declara para este método (HEAD usa el de GET); `None`: denegar."""
    declared = getattr(view, "required_permissions", None)
    method = "GET" if request.method == "HEAD" else request.method
    code = declared.get(method) if isinstance(declared, Mapping) else None
    return code if isinstance(code, str) else None


def request_context(request: Any) -> ExecutionContext | None:
    """Permisos efectivos de la petición: se leen una vez, dentro de su `tenant_scope`.

    `None` fuera de una ruta de tenant. Sin membresía activa responde 404, el mismo estado
    que da el middleware ante una organización inexistente.
    """
    tenant = context.current()
    if tenant is None:
        return None
    holder = getattr(request, "_request", request)  # DRF clona su Request (OPTIONS): una foto
    cached: ExecutionContext | None = getattr(holder, "_access_context", None)
    if cached is None:
        try:
            cached = execution_context(tenant)
        except AccessDenied:
            raise NotFound from None
        holder._access_context = cached  # vive lo que la petición; el motor lo liga al scope
    return cached


class HasPermission(BasePermission):
    def has_permission(self, request: Any, view: Any) -> bool:
        ectx, code = request_context(request), required_code(request, view)
        return ectx is not None and code is not None and has_permission(ectx, code)

    def has_object_permission(self, request: Any, view: Any, obj: Model) -> bool:
        ectx, code = request_context(request), required_code(request, view)
        if ectx is None or code is None:
            return False
        if not can(ectx, code, obj):
            raise NotFound  # nunca 403; red de seguridad: la vista debe consultar con scoped()
        return True


class ScopeFilter(BaseFilterBackend):
    """Listados y `get_object()`: solo las filas dentro del alcance, filtradas en SQL."""

    def filter_queryset(self, request: Any, queryset: QuerySet[Any], view: Any) -> QuerySet[Any]:
        ectx, code = request_context(request), required_code(request, view)
        if ectx is None or code is None:
            return queryset.none()
        return scoped(ectx, code, queryset)
