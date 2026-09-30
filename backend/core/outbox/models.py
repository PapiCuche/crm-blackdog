"""`outbox_events` (docs/fase-0/04 §O.2): eventos escritos en la transacción del cambio."""

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from core.db.models import TenantModel, uuid7_primary_key


class OutboxEvent(TenantModel):
    id = uuid7_primary_key()
    event_type = models.CharField(max_length=100)
    aggregate_type = models.CharField(max_length=50)
    aggregate_id = models.UUIDField()
    payload = models.JSONField(default=dict, encoder=DjangoJSONEncoder)
    # now() = hora de la transacción (Now() de Django es STATEMENT_TIMESTAMP en PostgreSQL):
    # coincide con audit_logs.occurred_at del mismo cambio.
    occurred_at = models.DateTimeField(
        db_default=models.Func(function="now", output_field=models.DateTimeField())
    )
    published_at = models.DateTimeField(null=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=100, blank=True, default="")  # solo la clase
    correlation_id = models.CharField(max_length=64, null=True)  # noqa: DJ001 — NULL = sin correlación

    class Meta:
        db_table = "outbox_events"
        indexes = [
            models.Index(
                fields=["organization_id", "occurred_at", "id"],
                name="outbox_events_pending_idx",
                condition=models.Q(published_at__isnull=True),
            )
        ]
