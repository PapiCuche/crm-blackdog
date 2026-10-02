"""Middleware de `/api/` (ADR-014 §1): el contrato de errores, por fuera de todo lo demás.

`ApiEnvelopeMiddleware` va el primero: cualquier error que salga sin el contrato (una ruta sin
resolver, un 400 de Django, una excepción en otro middleware) se convierte al cuerpo
`{"code": …}`, también con `DEBUG`, y toda respuesta de la API lleva una CSP cerrada: nunca
es un documento.
"""

import json
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse, HttpResponseBase

from core.api.errors import body, code_for, error_response

API_PREFIX = "/api/"
# Cabeceras que describen el cuerpo original: no valen para el cuerpo del contrato.
STALE = ("Content-Encoding", "Content-Disposition", "Content-Language", "ETag", "Last-Modified")
API_CSP = "default-src 'none'; frame-ancestors 'none'"
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
