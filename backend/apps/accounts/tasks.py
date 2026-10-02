"""Tareas de `accounts` (autodiscover de Celery)."""

from django.contrib.sessions.models import Session
from django.utils import timezone

from core.tenancy.celery import platform_task


@platform_task(name="accounts.purge_expired_sessions")
def purge_expired_sessions() -> int:
    """Borra las sesiones caducadas (D-F2-2): Django no las elimina por sí solo."""
    deleted, _ = Session.objects.filter(expire_date__lt=timezone.now()).delete()
    return deleted
