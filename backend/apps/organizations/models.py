"""Organizaciones (platform-owned, sin RLS de tenant; ADR-001 §2) y sus membresías."""

from django.conf import settings
from django.db import models

from core.db.models import TenantModel, uuid7_primary_key


class Organization(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE"
        TRIAL = "TRIAL"
        SUSPENDED = "SUSPENDED"

    id = uuid7_primary_key()
    slug = models.SlugField(max_length=63, unique=True)
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "organizations"

    def __str__(self) -> str:
        return self.slug


class OrganizationMembership(TenantModel):
    """Pertenencia de un usuario global a una organización (tenant-owned, ADR-002 §3.2).

    Es el "usuario" desde el punto de vista del CRM. No lleva rol: los roles se asignarán a la
    membresía (`membership_roles`, F2-04). Solo `ACTIVE` da acceso al tenant.
    """

    class Status(models.TextChoices):
        INVITED = "INVITED"
        ACTIVE = "ACTIVE"
        SUSPENDED = "SUSPENDED"
        DEACTIVATED = "DEACTIVATED"

    id = uuid7_primary_key()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Sin tenant activo: solo dentro de `user_scope`, donde RLS deja ver las filas del usuario.
    for_user = models.Manager()

    class Meta:
        db_table = "organization_memberships"
        default_manager_name = "objects"
        constraints = [
            models.UniqueConstraint(  # destino de las FK compuestas `*_user_id` (ADR-001)
                fields=["organization_id", "user"], name="organization_memberships_org_user_uq"
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["INVITED", "ACTIVE", "SUSPENDED", "DEACTIVATED"]),
                name="organization_memberships_status_ck",
            ),
        ]

    def __str__(self) -> str:
        return str(self.pk)
