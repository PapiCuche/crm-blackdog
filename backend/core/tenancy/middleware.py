"""Rutas de tenant HTTP `/api/v1/o/{slug}/…` (tenancy-context §2)."""

import re
from collections.abc import Callable

from django.http import HttpRequest, HttpResponseBase, JsonResponse

from core.tenancy.context import TenantContextError
from core.tenancy.resolution import OrganizationSuspended, TenantNotFound, resolve_tenant
from core.tenancy.scope import assert_clean_connection, tenant_scope

TENANT_PATH = re.compile(r"^/api/v1/o/(?P<slug>[-a-zA-Z0-9_]+)/")


def not_found() -> JsonResponse:
    """404 idéntico para organización inexistente, sin membresía o recurso de otro tenant."""
    return JsonResponse({"code": "NOT_FOUND"}, status=404)


class TenantResolutionMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponseBase]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        match = TENANT_PATH.match(request.path_info)
        if match is None:
            return self.get_response(request)  # auth/plataforma: sin contexto de tenant
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", True):
            return JsonResponse({"code": "NOT_AUTHENTICATED"}, status=401)
        assert_clean_connection()
        try:
            ctx = resolve_tenant(match["slug"], user, "http")  # correlation_id: F1-07
        except TenantNotFound:
            return not_found()
        except OrganizationSuspended:
            return JsonResponse({"code": "ORG_SUSPENDED"}, status=403)
        request.tenant = ctx  # type: ignore[attr-defined]
        with tenant_scope(ctx):  # toda la vista y su serialización en una transacción
            response = self.get_response(request)
            if response.streaming:
                raise TenantContextError("Streaming prohibido en rutas de tenant (usar Celery)")
            return response
