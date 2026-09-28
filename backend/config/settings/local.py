"""Desarrollo local. Nunca se usa en producción."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "django-insecure-local-only-not-for-production")
os.environ.setdefault("DATABASE_URL", "postgres://crm_app:change-me-local-app@localhost:5432/crm")

from config.settings.base import *  # noqa: E402,F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
