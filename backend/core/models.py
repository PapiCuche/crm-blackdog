"""Tablas del kernel (ADR-001 §2): tenant-owned con RLS."""

from django.db import models

from core.db.models import TenantModel


class OrgSequence(TenantModel):
    """Numeración comercial por organización y clave (ADR-004 §2). Solo vía `core.sequences`."""

    organization_id = models.UUIDField(editable=False)  # la PK ya lo indexa
    pk = models.CompositePrimaryKey("organization_id", "sequence_key")
    sequence_key = models.CharField(max_length=16)
    next_value = models.BigIntegerField()

    class Meta:
        db_table = "org_sequences"
