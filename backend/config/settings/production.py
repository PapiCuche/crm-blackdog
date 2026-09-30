"""Producción. Sin valores por defecto inseguros: falla al arrancar si falta algo crítico."""

import os
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

from config import env
from config.settings.base import *  # noqa: F403
from config.settings.base import ALLOWED_HOSTS, SECRET_KEY

# ADR-002 §1.1: la credencial del migrador (BYPASSRLS) es exclusiva del job de migraciones.
# web/worker/ws/beat se niegan a arrancar si la reciben. Solo se nombra la variable, nunca su valor.
FORBIDDEN_RUNTIME_VARIABLES = ("DATABASE_MIGRATOR_URL", "CRM_MIGRATOR_PASSWORD")
_leaked = [name for name in FORBIDDEN_RUNTIME_VARIABLES if name in os.environ]
if _leaked:
    raise ImproperlyConfigured(
        "El runtime recibió credenciales de migración prohibidas: " + ", ".join(_leaked)
    )

DEBUG = False
ENFORCE_RUNTIME_DB_ROLE = True  # ADR-002 §1.1: ni superusuario, ni BYPASSRLS, ni propietario
if env.boolean("DJANGO_DEBUG", False):
    raise ImproperlyConfigured("DEBUG no puede activarse en production")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS es obligatorio en production")
if SECRET_KEY.startswith("django-insecure") or len(SECRET_KEY) < 50:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY de production debe ser aleatoria y de 50+ caracteres"
    )

# ADR-008: storage con TLS. Vacío = AWS por defecto; explícito = https y sin credenciales.
_storage = urlsplit(env.optional("STORAGE_ENDPOINT_URL", ""))
if _storage.geturl() and (_storage.scheme != "https" or _storage.username or _storage.password):
    raise ImproperlyConfigured(
        "STORAGE_ENDPOINT_URL de production debe ser https y sin credenciales"
    )

# Loopback para las sondas locales (HEALTHCHECK del contenedor): se añade DESPUÉS de validar,
# así una DJANGO_ALLOWED_HOSTS vacía sigue fallando y el operador no necesita conocer la sonda.
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "[::1]")
ALLOWED_HOSTS = list(dict.fromkeys([*ALLOWED_HOSTS, *LOOPBACK_HOSTS]))

# Detrás del reverse proxy (ADR-003): el proxy termina TLS y envía X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [r"^health/"]  # sondas internas del orquestador
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"
CSRF_TRUSTED_ORIGINS = env.csv_list("DJANGO_CSRF_TRUSTED_ORIGINS")
