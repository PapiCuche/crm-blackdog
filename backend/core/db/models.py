"""Modelos tenant-owned (ADR-001 §5, tenancy-context §1.2)."""

from typing import Any

from django.db import models

from core.tenancy.context import TenantContextError, require


class TenantManager(models.Manager[Any]):
    """Filtra por la organización del contexto; sin `tenant_scope` falla en vez de devolver todo."""

    def get_queryset(self) -> models.QuerySet[Any]:
        return super().get_queryset().filter(organization_id=require().organization_id)


class TenantModel(models.Model):
    # FK a `organizations` en F1-04, cuando exista la tabla (se añade con CompositeTenantFK).
    organization_id = models.UUIDField(db_index=True, editable=False)

    objects = TenantManager()

    class Meta:
        abstract = True

    def save(self, *args: Any, **kwargs: Any) -> None:
        ctx = require()
        if self.organization_id is None:
            self.organization_id = ctx.organization_id  # siempre del contexto, nunca del payload
        elif self.organization_id != ctx.organization_id:
            raise TenantContextError("organization_id distinto del tenant del contexto")
        super().save(*args, **kwargs)
