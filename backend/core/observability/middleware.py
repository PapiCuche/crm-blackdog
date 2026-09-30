"""`request_id`/`correlation_id` por petición HTTP y log de finalización (ADR-011 §2).

Fase 1: no se confía en `X-Request-ID`/`X-Correlation-ID` entrantes (aún no hay un proxy de
confianza que los distinga de valores de Internet). Siempre se genera un UUIDv7 propio y la
petición raíz inicia su correlación. Solo método, ruta sin query, estado y duración: nunca
cuerpos, query string, cookies ni cabeceras.
"""

import time
from collections.abc import Callable

from django.http import HttpRequest, HttpResponseBase

from core.ids import new_id
from core.observability.context import bound
from core.observability.logging import get_logger

logger = get_logger("core.http")


class RequestContextMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponseBase]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        request_id = str(new_id())
        start = time.monotonic()
        with bound(request_id=request_id, correlation_id=request_id):
            response = self.get_response(request)  # Django convierte excepciones en 500
            response["X-Request-ID"] = request_id
            failed = response.status_code >= 500  # el traceback ya lo registra django.request
            tenant = getattr(request, "tenant", None)  # el scope ya cerró: IDs desde la petición
            ids = {} if tenant is None else {"organization_id": str(tenant.organization_id),
                   "user_id": str(tenant.user_id), "actor_type": tenant.actor_type}  # fmt: skip
            (logger.error if failed else logger.info)(
                "http.request.failed" if failed else "http.request.completed",
                method=request.method,
                path=request.path,
                status_code=response.status_code,
                duration_ms=round((time.monotonic() - start) * 1000, 1),
                **ids,
            )
            return response
