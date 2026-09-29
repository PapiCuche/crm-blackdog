"""Comandos administrativos con contexto explícito (tenancy-context §7).

`--reason` es obligatorio y se registra con el operador (auditoría persistente en F1-06).
"""

import getpass
import logging
from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from core.tenancy.context import TenantContext, require_no_tenant
from core.tenancy.resolution import organization_by_slug
from core.tenancy.scope import assert_clean_connection, tenant_scope

logger = logging.getLogger(__name__)


class PlatformCommand(BaseCommand):
    """Sin tenant: TenantManager falla dentro. No usa BYPASSRLS (crm_platform no existe)."""

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--reason", required=True, help="Motivo (se registra)")

    def handle(self, *args: Any, **options: Any) -> None:
        require_no_tenant(f"comando {self._name()}")  # también TenantCommand: abre su propio scope
        assert_clean_connection()
        logger.info("comando %s por %s: %s", self._name(), getpass.getuser(), options["reason"])
        self.handle_platform(**options)

    def handle_platform(self, **options: Any) -> None:
        raise NotImplementedError

    def _name(self) -> str:
        return type(self).__module__.rsplit(".", 1)[-1]


class TenantCommand(PlatformCommand):
    def add_arguments(self, parser: ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument("--org", required=True, help="Slug de la organización")

    def handle_platform(self, **options: Any) -> None:
        org = organization_by_slug(options["org"])
        if org is None:
            raise CommandError("Organización no encontrada")
        ctx = TenantContext(org.id, "command")  # actor SYSTEM
        with tenant_scope(ctx):
            self.handle_tenant(ctx, **options)

    def handle_tenant(self, ctx: TenantContext, **options: Any) -> None:
        raise NotImplementedError
