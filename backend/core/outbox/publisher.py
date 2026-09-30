"""Publisher del outbox (`@platform_task`): descubre tenants con eventos pendientes por una
función SECURITY DEFINER (solo IDs) y publica cada lote dentro del `tenant_scope` del tenant.
"""

import logging
from uuid import UUID

from django.db import connection
from django.db.models import F
from django.db.models.functions import Now

from core.outbox import handlers_for
from core.outbox.models import OutboxEvent
from core.tenancy.celery import platform_task
from core.tenancy.context import TenantContext
from core.tenancy.scope import tenant_scope

logger = logging.getLogger(__name__)


def pending_organizations(limit: int) -> list[UUID]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT public.outbox_pending_organizations(%s)", [limit])
        return [UUID(str(row[0])) for row in cursor.fetchall()]


def _publish(event: OutboxEvent) -> bool:
    try:
        for task in handlers_for(event.event_type):
            task.apply_async(
                kwargs={
                    "event_id": str(event.id),
                    "organization_id": str(event.organization_id),
                    "correlation_id": event.correlation_id,
                }
            )
    except Exception as exc:  # noqa: BLE001 — broker caído, etc.: se reintenta en el siguiente tick
        error = type(exc).__name__[:100]
        logger.warning("outbox: evento %s pendiente (%s)", event.id, error)
        OutboxEvent.objects.filter(id=event.id).update(attempts=F("attempts") + 1, last_error=error)
        return False
    OutboxEvent.objects.filter(id=event.id).update(
        published_at=Now(), attempts=F("attempts") + 1, last_error=""
    )
    return True


@platform_task(name="core.publish_outbox", ignore_result=True)
def publish_outbox(batch_size: int = 100, max_orgs: int = 50) -> int:
    published = 0
    for organization_id in pending_organizations(max_orgs):
        with tenant_scope(TenantContext(organization_id, "celery")):
            batch = (
                OutboxEvent.objects.select_for_update(skip_locked=True)
                .filter(published_at__isnull=True)
                .order_by("occurred_at", "id")[:batch_size]
            )
            published += sum(_publish(event) for event in batch)
    return published
