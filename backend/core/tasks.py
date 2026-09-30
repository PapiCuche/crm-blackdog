"""Tareas del kernel (autodiscover de Celery)."""

from core.outbox.publisher import publish_outbox

__all__ = ["publish_outbox"]
