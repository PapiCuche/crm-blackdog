"""Autenticación por sesión para DRF (ADR-014 §2).

La sesión la resuelve Django (`AuthenticationMiddleware`). Esta clase entrega el usuario a la
vista. `authenticate_header` nombra el esquema; que la falta de sesión sea un 401 y no un 403
lo garantiza el manejador de errores (`core.api.errors`), no esta cabecera.

El CSRF lo comprueba `ApiCsrfMiddleware` para todo `/api/`. Aquí se exige su marca: una vista
de DRF montada fuera de `/api/` rechaza los métodos no seguros en lugar de quedar sin control.
"""

from typing import Any

from rest_framework.authentication import BaseAuthentication
from rest_framework.request import Request

from core.api import AUTH_SCHEME, SAFE_METHODS
from core.api.errors import CSRF_FAILED, ApiError


class SessionAuthentication(BaseAuthentication):
    def authenticate(self, request: Request) -> tuple[Any, None] | None:
        raw = request._request
        if raw.method not in SAFE_METHODS and not getattr(raw, "csrf_processing_done", False):
            raise ApiError(CSRF_FAILED, 403)
        user = getattr(raw, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return None
        return (user, None) if getattr(user, "is_active", False) else None

    def authenticate_header(self, request: Request) -> str:
        return AUTH_SCHEME
