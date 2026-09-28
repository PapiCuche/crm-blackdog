"""Tests (pytest). La BD se toma de DATABASE_URL (en CI: servicio postgres:18.6)."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "django-insecure-test-only-not-for-production")
os.environ.setdefault("DATABASE_URL", "postgres://crm_app:change-me-local-app@localhost:5432/crm")

from config.settings.base import *  # noqa: E402,F403

ALLOWED_HOSTS = ["testserver"]
