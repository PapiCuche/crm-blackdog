import logging
from typing import Any

from django.apps import AppConfig
from django.db import connections, transaction
from django.db.models.signals import post_migrate

FIELDS = ["code", "module", "is_sensitive", "supports_scope"]
logger = logging.getLogger(__name__)


def sync_permissions(sender: Any, using: str = "default", **kwargs: Any) -> None:
    """Tras cada `migrate` (crm_migrator): deja `permissions` igual que el catálogo del código.

    Solo escribe lo que cambia (un despliegue sin cambios no bloquea filas). Un código que ya
    no está en el catálogo se borra si nadie lo tiene concedido; si está concedido se conserva
    y se avisa: retirarlo o renombrarlo exige una migración de datos que reescriba las
    concesiones. Cambiar `supports_scope` de un permiso concedido falla por la FK, a propósito.
    Añadir permisos no toca los roles que ya existen (OBS-F2-04-1).
    """
    from apps.access.catalog import PERMISSIONS
    from apps.access.models import Permission, RolePermission

    with connections[using].cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.permissions')")
        if cursor.fetchone()[0] is None:
            return  # `migrate access zero` o migración parcial
    table = Permission.objects.using(using)
    with transaction.atomic(using=using):
        current = {row[0]: row[1:] for row in table.values_list(*FIELDS)}
        wanted = {p.code: (p.module, p.is_sensitive, p.supports_scope) for p in PERMISSIONS}
        table.bulk_create(
            Permission(code=code, **dict(zip(FIELDS[1:], values, strict=True)))
            for code, values in wanted.items()
            if code not in current
        )
        for code, values in wanted.items():
            if code in current and current[code] != values:
                table.filter(code=code).update(**dict(zip(FIELDS[1:], values, strict=True)))
        granted = RolePermission._base_manager.using(using).values("permission_id")
        stale = table.exclude(code__in=wanted)
        stale.exclude(code__in=granted).delete()
        kept = list(stale.values_list("code", flat=True))
        if kept:
            logger.warning(
                "permisos fuera del catálogo que siguen concedidos", extra={"codes": kept}
            )


class AccessConfig(AppConfig):
    name = "apps.access"
    label = "access"

    def ready(self) -> None:
        post_migrate.connect(sync_permissions, sender=self, dispatch_uid="access_permissions")
