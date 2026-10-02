"""`platform_audit_logs` (ADR-013): auditoría de eventos sin organización.

- Platform-owned: sin `organization_id` y sin política de tenant (ADR-001 §2).
- crm_app: solo INSERT en la tabla padre. Sin SELECT, UPDATE, DELETE ni TRUNCATE, y ningún
  privilegio directo sobre las particiones: el runtime escribe y no puede leer ni alterar.
- `platform_audit_ensure_partitions(n)`: mes actual + n, igual que `audit_ensure_partitions`.
  Propiedad de crm_migrator, sin EXECUTE para PUBLIC ni crm_app. No es SECURITY DEFINER.
"""

from typing import Any

from django.conf import settings
from django.db import migrations

TABLE = """
CREATE TABLE public.platform_audit_logs (
  id uuid NOT NULL DEFAULT uuidv7(),
  occurred_at timestamptz NOT NULL DEFAULT now(),
  actor_type varchar(16) NOT NULL
    CHECK (actor_type IN ('USER', 'SYSTEM', 'PLATFORM_STAFF', 'ANONYMOUS')),
  actor_id uuid NULL,
  identifier_hash varchar(64) NULL CHECK (identifier_hash ~ '^[0-9a-f]{64}$'),
  action varchar(100) NOT NULL,
  entity_type varchar(50) NULL,
  entity_id uuid NULL,
  metadata jsonb NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(metadata) = 'object'),
  ip inet NULL,
  user_agent varchar(512) NULL,
  request_id varchar(64) NULL,
  correlation_id varchar(64) NULL,
  result varchar(8) NOT NULL DEFAULT 'SUCCESS' CHECK (result IN ('SUCCESS', 'DENIED', 'FAILED')),
  CHECK (entity_id IS NULL OR entity_type IS NOT NULL),
  PRIMARY KEY (occurred_at, id)
) PARTITION BY RANGE (occurred_at)
"""

FUNCTION = """
CREATE FUNCTION public.platform_audit_ensure_partitions(p_months integer) RETURNS integer
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
    part := 'platform_audit_logs_y' || to_char(m, 'YYYY') || 'm' || to_char(m, 'MM');
    IF to_regclass('public.' || part) IS NULL THEN
      EXECUTE format('CREATE TABLE public.%I PARTITION OF public.platform_audit_logs '
                     'FOR VALUES FROM (%L) TO (%L)',
                     part, m::timestamp AT TIME ZONE 'UTC',
                     (m + interval '1 month')::timestamp AT TIME ZONE 'UTC');
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
    # Los privilegios por defecto del init dan DML completo a crm_app: se deja solo INSERT.
    schema_editor.execute(f"REVOKE ALL ON public.platform_audit_logs FROM {app_role}")
    schema_editor.execute(f"GRANT INSERT ON public.platform_audit_logs TO {app_role}")
    # params=None: sin interpolación del driver (el cuerpo plpgsql contiene `%`).
    schema_editor.execute(FUNCTION.format(app_role_literal=literal), None)
    schema_editor.execute(
        f"ALTER FUNCTION public.platform_audit_ensure_partitions(integer) OWNER TO {owner}"
    )
    schema_editor.execute(
        "REVOKE ALL ON FUNCTION public.platform_audit_ensure_partitions(integer) FROM PUBLIC"
    )
    schema_editor.execute("SELECT public.platform_audit_ensure_partitions(12)")


def drop(apps: Any, schema_editor: Any) -> None:
    schema_editor.execute("DROP TABLE IF EXISTS public.platform_audit_logs CASCADE")
    schema_editor.execute(
        "DROP FUNCTION IF EXISTS public.platform_audit_ensure_partitions(integer)"
    )


class Migration(migrations.Migration):
    dependencies = [("audit", "0001_audit_logs")]
    operations = [migrations.RunPython(create, drop)]
