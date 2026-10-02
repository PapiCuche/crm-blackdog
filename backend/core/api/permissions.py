"""Clases de permiso de las rutas de PLATAFORMA (ADR-014 §4): todo `/api/` fuera de
`/api/v1/o/{slug}/`. Se eligen por la ruta, nunca por el actor.

Ninguna autoriza nada dentro de un tenant: con un `tenant_scope` activo deniegan siempre, así
que no sirven para saltarse `HasPermission` en una ruta de tenant.
"""

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from core.tenancy import context

TENANT_PREFIX = "/api/v1/o/"


def _outside_tenant(request: Request) -> bool:
    return context.current() is None and not request.path_info.startswith(TENANT_PREFIX)


class Public(BasePermission):
    """Acceso sin sesión: login, token CSRF, contrato OpenAPI."""

    def has_permission(self, request: Request, view: Any) -> bool:
        return _outside_tenant(request)


class Authenticated(BasePermission):
    """Sesión válida de un usuario activo: logout, sesión actual, mis organizaciones."""

    def has_permission(self, request: Request, view: Any) -> bool:
        return _outside_tenant(request) and request.successful_authenticator is not None
