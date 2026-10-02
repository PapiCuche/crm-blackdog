from typing import Any

from django.apps import AppConfig
from django.db import connections
from django.db.models.signals import post_migrate

PARTITION_MONTHS = 12  # horizonte: mes actual + 12; sin partición DEFAULT (falla cerrado)


FUNCTIONS = ("audit_ensure_partitions", "platform_audit_ensure_partitions")  # ADR-011, ADR-013


def ensure_partitions(sender: Any, using: str = "default", **kwargs: Any) -> None:
    """Tras cada `migrate` (job de migraciones, crm_migrator): crea las particiones que falten."""
    with connections[using].cursor() as cursor:
        for function in FUNCTIONS:
            cursor.execute("SELECT to_regprocedure(%s)", [f"public.{function}(integer)"])
            if cursor.fetchone()[0] is not None:
                cursor.execute(f"SELECT public.{function}(%s)", [PARTITION_MONTHS])


class AuditConfig(AppConfig):
    name = "apps.audit"
    label = "audit"

    def ready(self) -> None:
        post_migrate.connect(ensure_partitions, sender=self, dispatch_uid="audit_partitions")
