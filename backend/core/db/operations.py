"""Operaciones de migración reutilizables para RLS (ADR-002 §3–§4)."""

from typing import Any

from django.conf import settings
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.operations.base import Operation
from django.db.migrations.state import ProjectState

POLICY = "tenant_isolation"


def _table(state: ProjectState, app_label: str, model_name: str) -> str:
    return str(state.apps.get_model(app_label, model_name)._meta.db_table)


class EnableRLS(Operation):
    """ENABLE + FORCE RLS y una única política PERMISSIVE `tenant_isolation`."""

    reversible = True

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def state_forwards(self, app_label: str, state: ProjectState) -> None:
        pass

    def database_forwards(
        self,
        app_label: str,
        schema_editor: BaseDatabaseSchemaEditor,
        from_state: ProjectState,
        to_state: ProjectState,
    ) -> None:
        t = schema_editor.quote_name(_table(to_state, app_label, self.model_name))
        condition = "organization_id = app_current_tenant()"
        schema_editor.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY")
        schema_editor.execute(
            f"CREATE POLICY {POLICY} ON {t} USING ({condition}) WITH CHECK ({condition})"
        )

    def database_backwards(
        self,
        app_label: str,
        schema_editor: BaseDatabaseSchemaEditor,
        from_state: ProjectState,
        to_state: ProjectState,
    ) -> None:
        t = schema_editor.quote_name(_table(from_state, app_label, self.model_name))
        schema_editor.execute(f"DROP POLICY IF EXISTS {POLICY} ON {t}")
        schema_editor.execute(f"ALTER TABLE {t} NO FORCE ROW LEVEL SECURITY")
        schema_editor.execute(f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY")

    def describe(self) -> str:
        return f"Enable RLS on {self.model_name}"


class CompositeTenantFK(Operation):
    """FK (organization_id, <fk>) → referenciada(organization_id, id): misma organización en BD."""

    reversible = True

    def __init__(self, model_name: str, field: str, to_model: str, name: str) -> None:
        self.model_name, self.field, self.to_model, self.name = model_name, field, to_model, name

    def state_forwards(self, app_label: str, state: ProjectState) -> None:
        pass

    def database_forwards(
        self,
        app_label: str,
        schema_editor: BaseDatabaseSchemaEditor,
        from_state: ProjectState,
        to_state: ProjectState,
    ) -> None:
        q = schema_editor.quote_name
        model = to_state.apps.get_model(app_label, self.model_name)
        column = model._meta.get_field(self.field).column
        ref = _table(to_state, app_label, self.to_model)
        unique = f"{ref}_org_id_uq"
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_constraint WHERE conname = %s", [unique])
            exists = cursor.fetchone() is not None
        if not exists:
            schema_editor.execute(
                f"ALTER TABLE {q(ref)} ADD CONSTRAINT {q(unique)} UNIQUE (organization_id, id)"
            )
        schema_editor.execute(
            f"ALTER TABLE {q(model._meta.db_table)} ADD CONSTRAINT {q(self.name)} "
            f"FOREIGN KEY (organization_id, {q(column)}) REFERENCES {q(ref)} (organization_id, id)"
        )

    def database_backwards(
        self,
        app_label: str,
        schema_editor: BaseDatabaseSchemaEditor,
        from_state: ProjectState,
        to_state: ProjectState,
    ) -> None:
        table = _table(from_state, app_label, self.model_name)
        q = schema_editor.quote_name
        schema_editor.execute(f"ALTER TABLE {q(table)} DROP CONSTRAINT IF EXISTS {q(self.name)}")

    def describe(self) -> str:
        return f"Composite tenant FK {self.name}"


class SecurityDefinerFunction(Operation):
    """Función SECURITY DEFINER con los requisitos de ADR-002 §3.3 (siempre REVOKE/GRANT)."""

    reversible = True

    def __init__(self, name: str, arguments: str, argtypes: str, returns: str, body: str) -> None:
        self.name, self.arguments, self.argtypes = name, arguments, argtypes
        self.returns, self.body = returns, body

    def state_forwards(self, app_label: str, state: ProjectState) -> None:
        pass

    def database_forwards(
        self, app_label: str, schema_editor: BaseDatabaseSchemaEditor, *a: Any
    ) -> None:
        signature = f"public.{self.name}({self.argtypes})"
        app_role = schema_editor.quote_name(settings.DB_APP_ROLE)
        schema_editor.execute(
            f"CREATE FUNCTION public.{self.name}({self.arguments}) RETURNS {self.returns} "
            f"LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public "
            f"AS $fn$ {self.body} $fn$"
        )
        schema_editor.execute(f"ALTER FUNCTION {signature} OWNER TO CURRENT_USER")
        schema_editor.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
        schema_editor.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO {app_role}")

    def database_backwards(
        self, app_label: str, schema_editor: BaseDatabaseSchemaEditor, *a: Any
    ) -> None:
        schema_editor.execute(f"DROP FUNCTION IF EXISTS public.{self.name}({self.argtypes})")

    def describe(self) -> str:
        return f"SECURITY DEFINER function {self.name}"
