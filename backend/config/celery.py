"""App Celery (tenancy-context §3). Broker y colas: F1-10 (stack local)."""

import os

from celery import Celery

from core.tenancy.celery import TenancyCheck

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("crm")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.steps["worker"].add(TenancyCheck)  # sin tareas sin decorar o el worker no arranca
