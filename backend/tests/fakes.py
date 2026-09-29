"""Dobles de test: autenticación y membresías simuladas (la tabla real llega en la Fase 2)."""

from collections.abc import Callable
from typing import Any
from uuid import UUID

from django.http import HttpRequest, HttpResponseBase

MEMBERS: set[tuple[UUID, UUID]] = set()  # (user_id, organization_id)


def membership(user: Any, organization_id: UUID) -> UUID | None:
    return user if (user, organization_id) in MEMBERS else None


class FakeAuthMiddleware:
    """`X-Test-User: <uuid>` → request.user. Solo en config.settings.test."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponseBase]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        header = request.headers.get("X-Test-User")
        request.user = UUID(header) if header else None  # type: ignore[assignment]
        return self.get_response(request)
