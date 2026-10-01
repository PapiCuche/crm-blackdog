"""Servicios de `access`. Solo el modelo: sin permisos efectivos ni asignaciones (F2-05, F2-06)."""

from apps.access.catalog import BY_CODE, ROLE_TEMPLATES
from apps.access.models import Role, RolePermission
from core.tenancy.context import TenantContext
from core.tenancy.scope import require_scope


def clone_role_templates(ctx: TenantContext) -> list[Role]:
    """Crea en la organización de `ctx` los roles plantilla que falten (idempotente).

    Un rol cuyo código ya existe no se toca: ni su nombre ni sus concesiones, de modo que las
    ediciones de la organización se conservan. El rol Owner se reconoce por `is_owner_role`,
    no por su código. Devuelve solo los roles creados en esta llamada.
    """
    alias = require_scope(ctx)  # misma transacción y GUC que el tenant_scope activo
    roles = Role.objects.using(alias)
    existing = set(roles.values_list("code", flat=True))
    has_owner = roles.filter(is_owner_role=True).exists()
    created = []
    for template in ROLE_TEMPLATES:
        if template.code in existing or (template.is_owner_role and has_owner):
            continue
        role = Role(
            code=template.code,
            name=template.name,
            is_system=True,
            is_owner_role=template.is_owner_role,
        )
        role.save(using=alias)
        RolePermission.objects.using(alias).bulk_create(
            RolePermission(
                organization_id=ctx.organization_id,
                role=role,
                permission_id=code,
                supports_scope=BY_CODE[code].supports_scope,
                scope=scope,
            )
            for code, scope in template.grants.items()
        )
        created.append(role)
    return created
