"""Los dos middlewares de `/api/` (ADR-014 §1–2).

`ApiEnvelopeMiddleware` va el primero, por fuera de todos los demás: cualquier error que salga
sin el contrato (una ruta sin resolver, un 400 de Django, una excepción en otro middleware)
se convierte al cuerpo `{"code": …}`, también con `DEBUG`, y toda respuesta de la API lleva
una CSP cerrada: nunca es un documento.

`ApiCsrfMiddleware` va justo antes de resolver el tenant: exige el token CSRF en todo método
no seguro, haya sesión o no. `APIView.as_view()` marca las vistas de DRF como exentas, así que
el control no puede depender de la vista. El token solo se acepta en la cabecera `X-CSRFToken`:
el cuerpo no se lee antes de autenticar.
"""

import json
import logging
from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.middleware import csrf
from django.middleware.csrf import (
    REASON_CSRF_TOKEN_MISSING,
    REASON_NO_CSRF_COOKIE,
    CsrfViewMiddleware,
    InvalidTokenFormat,
    RejectRequest,
)

from core.api import SAFE_METHODS
from core.api.errors import CSRF_FAILED, body, code_for, error_response

API_PREFIX = "/api/"
# Cabeceras que describen el cuerpo original: no valen para el cuerpo del contrato.
STALE = ("Content-Encoding", "Content-Disposition", "Content-Language", "ETag", "Last-Modified")
API_CSP = "default-src 'none'; frame-ancestors 'none'"
logger = logging.getLogger("django.security.csrf")
GetResponse = Callable[[HttpRequest], HttpResponseBase]


class ApiEnvelopeMiddleware:
    def __init__(self, get_response: GetResponse) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        response = self.get_response(request)
        path = request.path_info
        if path != API_PREFIX.rstrip("/") and not path.startswith(API_PREFIX):
            return response
        content_type = response.headers.get("Content-Type", "")
        if response.status_code >= 400 and "json" not in content_type:
            response = self._contract(response)
        response.headers["Content-Security-Policy"] = API_CSP
        return response

    @staticmethod
    def _contract(original: HttpResponseBase) -> HttpResponseBase:
        """El mismo estado con el cuerpo del contrato, conservando cabeceras y cookies."""
        code = code_for(original.status_code)
        if original.streaming or not isinstance(original, HttpResponse):
            response: HttpResponse = error_response(code, original.status_code)
            for name, value in original.headers.items():
                if name.lower() not in ("content-type", "content-length"):
                    response.headers[name] = value
            response.cookies = original.cookies
            original.close()  # p. ej., el archivo abierto de un FileResponse
        else:  # en el sitio
            response = original
            response.headers["Content-Type"] = "application/json"
            response.content = json.dumps(body(code), separators=(",", ":")).encode()
        for name in STALE:
            response.headers.pop(name, None)
        response.headers["Content-Length"] = str(len(response.content))
        return response


class _CsrfCheck(CsrfViewMiddleware):
    def _reject(self, request: HttpRequest, reason: str) -> Any:
        return reason  # al cliente solo le llega el código; el motivo va al log

    def _check_token(self, request: HttpRequest) -> None:
        """Como el de Django, pero el token solo viaja en la cabecera: nunca se lee el cuerpo.

        Usa tres funciones internas de Django 5.2 (`_get_secret`, `_check_token_format`,
        `_does_token_match`): si una actualización las cambia, fallan los tests de CSRF.
        """
        try:
            secret = self._get_secret(request)  # type: ignore[attr-defined]
        except InvalidTokenFormat as error:
            raise RejectRequest(f"CSRF cookie {error.reason}.") from error
        if secret is None:
            raise RejectRequest(REASON_NO_CSRF_COOKIE)
        try:
            token = request.META[settings.CSRF_HEADER_NAME]
        except KeyError:
            raise RejectRequest(REASON_CSRF_TOKEN_MISSING) from None
        try:
            csrf._check_token_format(token)  # type: ignore[attr-defined]
        except InvalidTokenFormat as error:
            raise RejectRequest(f"CSRF token {error.reason}.") from error
        if not csrf._does_token_match(token, secret):  # type: ignore[attr-defined]
            raise RejectRequest("CSRF token incorrect.")


def _any_view(request: HttpRequest) -> HttpResponseBase:
    """Vista de referencia para el control: no es `csrf_exempt`, a diferencia de las de DRF."""
    raise NotImplementedError


class ApiCsrfMiddleware:
    def __init__(self, get_response: GetResponse) -> None:
        self.get_response = get_response
        self.csrf = _CsrfCheck(get_response)

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        if request.path_info.startswith(API_PREFIX) and request.method not in SAFE_METHODS:
            reason = self.csrf.process_view(request, _any_view, (), {})
            if reason:  # si pasa, Django marca `request.csrf_processing_done`
                logger.warning("CSRF rechazado (%s): %s", reason, request.path)
                return error_response(CSRF_FAILED, 403)
        return self.get_response(request)
