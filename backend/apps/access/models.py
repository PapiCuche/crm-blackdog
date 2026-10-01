"""Modelo RBAC (ADR-003 §5): permisos globales; roles y concesiones por organización.

Solo el modelo: los permisos efectivos y su verificación llegan en F2-05. Las FK entre tablas
de tenant son compuestas con `organization_id` (migración), de modo que la BD impide mezclar
organizaciones; por eso las FK simples de Django no crean constraint ni índice propios
(`db_constraint=False, db_index=False`): la FK real es la compuesta.
"""

from django.db import models
from django.db.models.functions import Now

from apps.access.catalog import Scope
from core.db.models import TenantModel, uuid7_primary_key


class Permission(models.Model):
    """Catálogo global, sincronizado desde `catalog.PERMISSIONS`; solo lectura para el runtime."""

    id = (
        uuid7_primary_key()
    )  # ADR-004 §1; la clave natural que referencian las concesiones es `code`
    code = models.CharField(max_length=64, unique=True)
    module = models.CharField(max_length=32)
    is_sensitive = models.BooleanField()
    supports_scope = models.BooleanField()

    class Meta:
        db_table = "permissions"
        constraints = [
            models.UniqueConstraint(  # destino de la FK que fija `supports_scope` en la concesión
                fields=["code", "supports_scope"], name="permissions_code_scope_uq"
            ),
            models.CheckConstraint(  # el alcance nunca forma parte del código
                condition=models.Q(code__regex=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
                & ~models.Q(code__regex=r"\.(own|team|branch|organization)$"),
                name="permissions_code_ck",
            ),
        ]

    def __str__(self) -> str:
        return self.code


class Role(TenantModel):
    id = uuid7_primary_key()
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    is_system = models.BooleanField(default=False)  # clonado de una plantilla
    is_owner_role = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "roles"
        constraints = [
            models.UniqueConstraint(fields=["organization_id", "code"], name="roles_org_code_uq"),
            models.UniqueConstraint(fields=["organization_id", "id"], name="roles_org_id_uq"),
            models.UniqueConstraint(  # el rol Owner se localiza por este flag, nunca por código
                fields=["organization_id"],
                condition=models.Q(is_owner_role=True),
                name="roles_one_owner_uq",
            ),
        ]


class RolePermission(TenantModel):
    """Concesión de un permiso a un rol, con su alcance (NULL si el permiso no lo admite)."""

    id = uuid7_primary_key()
    role = models.ForeignKey(
        Role, models.CASCADE, related_name="grants", db_constraint=False, db_index=False
    )
    permission = models.ForeignKey(
        Permission,
        models.PROTECT,
        to_field="code",
        db_column="permission_code",
        related_name="+",
        db_constraint=False,
        db_index=False,
    )
    supports_scope = models.BooleanField(editable=False)  # copia fijada por FK al catálogo
    scope = models.CharField(max_length=12, null=True, choices=Scope.choices)  # noqa: DJ001
    created_at = models.DateTimeField(db_default=Now())

    class Meta:
        db_table = "role_permissions"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "role", "permission"],
                name="role_permissions_role_permission_uq",
            ),
            models.CheckConstraint(
                condition=models.Q(supports_scope=True, scope__isnull=False, scope__in=Scope.values)
                | models.Q(supports_scope=False, scope__isnull=True),
                name="role_permissions_scope_ck",
            ),
        ]


class MembershipRole(TenantModel):
    """Rol asignado a una membresía (N:M). Ni el usuario ni la membresía llevan un rol propio."""

    id = uuid7_primary_key()
    membership = models.ForeignKey(
        "organizations.OrganizationMembership",
        models.PROTECT,
        related_name="+",
        db_constraint=False,
        db_index=False,
    )
    role = models.ForeignKey(
        Role, models.PROTECT, related_name="assignments", db_constraint=False, db_index=False
    )
    created_at = models.DateTimeField(db_default=Now())

    class Meta:
        db_table = "membership_roles"
        constraints = [
            models.UniqueConstraint(
                fields=["organization_id", "membership", "role"],
                name="membership_roles_membership_role_uq",
            )
        ]
        indexes = [  # lado referenciante de la FK al rol y "miembros de un rol"
            models.Index(fields=["organization_id", "role"], name="membership_roles_org_role_idx")
        ]
