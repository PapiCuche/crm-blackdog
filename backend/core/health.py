"""Health checks (ADR-011 §4): sin versiones, hosts ni detalles de error."""

import logging

from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

logger = logging.getLogger(__name__)


@never_cache
@require_safe
def live(request: HttpRequest) -> JsonResponse:
    """El proceso responde. No toca dependencias (liveness)."""
    return JsonResponse({"status": "ok"})


def _database_ok() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return bool(cursor.fetchone() == (1,))
    except Exception as exc:  # noqa: BLE001 — cualquier fallo = no listo; el detalle solo va al log
        logger.warning("readiness: base de datos no disponible (%s)", type(exc).__name__)
        return False


@never_cache
@require_safe
def ready(request: HttpRequest) -> JsonResponse:
    """Dependencias listas (readiness). Redis y storage se añaden cuando existan."""
    checks = {"database": "ok" if _database_ok() else "fail"}
    healthy = all(v == "ok" for v in checks.values())
    return JsonResponse(
        {"status": "ok" if healthy else "fail", "checks": checks}, status=200 if healthy else 503
    )
