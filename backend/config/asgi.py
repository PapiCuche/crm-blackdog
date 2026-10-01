"""ASGI: HTTP (Django) + WebSocket (Channels, tenancy-context §4)."""

import logging
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

django_application = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import (  # noqa: E402
    AllowedHostsOriginValidator,
    WebsocketDenier,
)
from django.conf import settings  # noqa: E402
from django.db import OperationalError, connection  # noqa: E402
from django.urls import re_path  # noqa: E402

# Rutas WS de tenant (`/ws/o/<org_slug>/…`, consumers con TenantConsumerMixin): llegan con sus
# módulos. La sesión (AuthMiddlewareStack) se añade con la autenticación de la Fase 2.
websocket_urlpatterns: list[object] = []
application = ProtocolTypeRouter(
    {
        "http": django_application,
        # Ruta WS desconocida: rechazo limpio (403), no un 500 por "No route found".
        "websocket": AllowedHostsOriginValidator(
            URLRouter([*websocket_urlpatterns, re_path(r"", WebsocketDenier.as_asgi())])
        ),
    }
)

if settings.ENFORCE_RUNTIME_DB_ROLE:
    # ADR-002 §1.1: con un rol no apto el proceso no arranca (el receptor de
    # connection_created lanza ImproperlyConfigured). BD caída ≠ rol no apto: se registra y
    # se reintenta en la siguiente conexión.
    try:
        connection.ensure_connection()
    except OperationalError:
        logging.getLogger(__name__).warning(
            "BD no disponible al arrancar; se verificará al conectar"
        )
    finally:
        connection.close()
