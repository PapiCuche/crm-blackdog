"""ASGI (HTTP). Channels (WebSocket) se añade en F1-04."""

import logging
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

application = get_asgi_application()

from django.conf import settings  # noqa: E402
from django.db import OperationalError, connection  # noqa: E402

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
