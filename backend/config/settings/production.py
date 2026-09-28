"""Producción. Sin valores por defecto inseguros: falla al arrancar si falta algo crítico."""

from django.core.exceptions import ImproperlyConfigured

from config import env
from config.settings.base import *  # noqa: F403
from config.settings.base import ALLOWED_HOSTS, SECRET_KEY

DEBUG = False
if env.boolean("DJANGO_DEBUG", False):
    raise ImproperlyConfigured("DEBUG no puede activarse en production")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS es obligatorio en production")
if SECRET_KEY.startswith("django-insecure") or len(SECRET_KEY) < 50:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY de production debe ser aleatoria y de 50+ caracteres"
    )

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
