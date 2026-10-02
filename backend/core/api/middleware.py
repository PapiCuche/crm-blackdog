"""Middleware de `/api/` (ADR-014 §1): el contrato de errores, por fuera de todo lo demás.

`ApiEnvelopeMiddleware` va el primero: cualquier error que salga sin el contrato (una ruta sin
resolver, un 400 de Django, una excepción en otro middleware) se convierte al cuerpo
`{"code": …}`, también con `DEBUG`, y toda respuesta de la API lleva una CSP cerrada: nunca
es un documento.
"""

import json
from collections.abc import Callable

from django.http import HttpRequest, HttpResponseBase

from core.api.errors import body, code_for, error_response

API_PREFIX = "/api/"
API_CSP = "default-src 'none'; frame-ancestors 'none'"
GetResponse = Callable[[HttpRequest], HttpResponseBase]


class ApiEnvelopeMiddleware:
    def __init__(self, get_response: GetResponse) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        response = self.get_response(request)
        if not request.path_info.startswith(API_PREFIX):
            return response
        content_type = response.headers.get("Content-Type", "")
        if response.status_code >= 400 and "json" not in content_type:
            code = code_for(response.status_code)
            if response.streaming or not hasattr(response, "content"):
                response = error_response(code, response.status_code)
            else:  # en el sitio: se conservan las cabeceras y cookies ya puestas
                response.content = json.dumps(body(code), separators=(",", ":"))
                response.headers["Content-Type"] = "application/json"
                response.headers["Content-Length"] = str(len(response.content))
        response.headers["Content-Security-Policy"] = API_CSP
        return response
