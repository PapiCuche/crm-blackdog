"""Funciones de contexto para las políticas RLS (ADR-002 §3.1)."""

from typing import Any

from django.conf import settings
from django.db import migrations

FUNCTIONS = ("app_current_tenant", "app_current_user")


def create(apps: Any, schema_editor: Any) -> None:
    app_role = schema_editor.quote_name(settings.DB_APP_ROLE)
    for name, setting in zip(FUNCTIONS, ("app.tenant_id", "app.user_id"), strict=True):
        schema_editor.execute(
            f"CREATE FUNCTION public.{name}() RETURNS uuid LANGUAGE sql STABLE "
            f"AS $fn$ SELECT NULLIF(current_setting('{setting}', true), '')::uuid $fn$"
        )
        # PUBLIC no tiene EXECUTE (privilegios por defecto del init): las políticas lo necesitan.
        schema_editor.execute(f"GRANT EXECUTE ON FUNCTION public.{name}() TO {app_role}")


def drop(apps: Any, schema_editor: Any) -> None:
    for name in FUNCTIONS:
        schema_editor.execute(f"DROP FUNCTION IF EXISTS public.{name}()")


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [migrations.RunPython(create, drop)]
