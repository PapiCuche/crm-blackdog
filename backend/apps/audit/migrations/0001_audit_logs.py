"""`audit_logs` (ADR-011; docs/fase-0/04 §N): particionada por mes, append-only para crm_app.

- Tenant-owned: `organization_id NOT NULL` + FK, RLS ENABLE + FORCE y `tenant_isolation`
  (en la tabla padre y en cada partición, que T4 también inspecciona).
- crm_app: solo SELECT e INSERT en la tabla padre; ningún privilegio directo sobre las
  particiones (los privilegios por defecto del init se revocan en cada partición nueva).
- `audit_ensure_partitions(n)`: crea el mes actual + n. Propiedad de crm_migrator y sin
  EXECUTE para PUBLIC/crm_app (el runtime no tiene DDL). SQL dinámico con `format(%I/%L)`:
  su única entrada es un entero acotado. No es SECURITY DEFINER.
"""

from typing import Any

from django.conf import settings
from django.db import migrations

POLICY = (
    "CREATE POLICY tenant_isolation ON {table} USING (organization_id = app_current_tenant()) "
    "WITH CHECK (organization_id = app_current_tenant())"
)

TABLE = """
CREATE TABLE public.audit_logs (
  id uuid NOT NULL DEFAULT uuidv7(),
  organization_id uuid NOT NULL REFERENCES public.organizations (id),
  occurred_at timestamptz NOT NULL DEFAULT now(),
  actor_type varchar(16) NOT NULL
    CHECK (actor_type IN ('USER', 'AI_AGENT', 'SYSTEM', 'INTEGRATION', 'PLATFORM_STAFF')),
  actor_id uuid NULL,
  actor_label varchar(200) NULL,
  impersonated_by_user_id uuid NULL,
  action varchar(100) NOT NULL,
  entity_type varchar(50) NOT NULL,
  entity_id uuid NULL,
  entity_label varchar(200) NULL,
  changes jsonb NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(changes) = 'object'),
  metadata jsonb NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(metadata) = 'object'),
  ip inet NULL,
  user_agent varchar(512) NULL,
  request_id varchar(64) NULL,
  correlation_id varchar(64) NULL,
  result varchar(8) NOT NULL DEFAULT 'SUCCESS' CHECK (result IN ('SUCCESS', 'DENIED', 'FAILED')),
  PRIMARY KEY (organization_id, occurred_at, id)
) PARTITION BY RANGE (occurred_at)
"""

FUNCTION = """
CREATE FUNCTION public.audit_ensure_partitions(p_months integer) RETURNS integer
LANGUAGE plpgsql VOLATILE SET search_path = pg_catalog, public AS $fn$
DECLARE
  m date := date_trunc('month', now() AT TIME ZONE 'UTC')::date;
  part text;
  created integer := 0;
BEGIN
  IF p_months IS NULL OR p_months < 0 OR p_months > 36 THEN
    RAISE EXCEPTION 'p_months fuera de rango: %', p_months;
  END IF;
  FOR i IN 0..p_months LOOP
    part := 'audit_logs_y' || to_char(m, 'YYYY') || 'm' || to_char(m, 'MM');
    IF to_regclass('public.' || part) IS NULL THEN
      EXECUTE format('CREATE TABLE public.%I PARTITION OF public.audit_logs '
                     'FOR VALUES FROM (%L) TO (%L)',
                     part, m::timestamp AT TIME ZONE 'UTC',
                     (m + interval '1 month')::timestamp AT TIME ZONE 'UTC');
      EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', part);
      EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', part);
      EXECUTE format('{policy}', part);
      EXECUTE format('REVOKE ALL ON public.%I FROM %I', part, {app_role_literal});
      created := created + 1;
    END IF;
    m := (m + interval '1 month')::date;
  END LOOP;
  RETURN created;
END
$fn$
"""


def create(apps: Any, schema_editor: Any) -> None:
    q = schema_editor.quote_name
    app_role, owner = q(settings.DB_APP_ROLE), q(settings.DB_MIGRATOR_ROLE)
    literal = "'" + settings.DB_APP_ROLE.replace("'", "''") + "'"
    schema_editor.execute(TABLE)
    schema_editor.execute("ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY")
    schema_editor.execute("ALTER TABLE public.audit_logs FORCE ROW LEVEL SECURITY")
    schema_editor.execute(POLICY.format(table="public.audit_logs"))
    schema_editor.execute(f"REVOKE UPDATE, DELETE, TRUNCATE ON public.audit_logs FROM {app_role}")
    policy = POLICY.format(table="public.%I").replace("'", "''")
    # params=None: sin interpolación del driver (el cuerpo plpgsql contiene `%`).
    schema_editor.execute(FUNCTION.format(policy=policy, app_role_literal=literal), None)
    schema_editor.execute(
        f"ALTER FUNCTION public.audit_ensure_partitions(integer) OWNER TO {owner}"
    )
    schema_editor.execute(
        "REVOKE ALL ON FUNCTION public.audit_ensure_partitions(integer) FROM PUBLIC"
    )
    schema_editor.execute("SELECT public.audit_ensure_partitions(12)")


def drop(apps: Any, schema_editor: Any) -> None:
    schema_editor.execute("DROP TABLE IF EXISTS public.audit_logs CASCADE")
    schema_editor.execute("DROP FUNCTION IF EXISTS public.audit_ensure_partitions(integer)")


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("core", "0001_tenancy_functions"),
        ("organizations", "0002_alter_organization_id"),
    ]
    operations = [migrations.RunPython(create, drop)]
