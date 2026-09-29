"""Selectores públicos de plataforma (docs/architecture/module-dependencies.md §3)."""

from apps.organizations.models import Organization
from core.tenancy.resolution import OrganizationRef


def organization_by_slug(slug: str) -> OrganizationRef | None:
    row = Organization.objects.filter(slug=slug).values_list("id", "status").first()
    return OrganizationRef(*row) if row else None
