#!/bin/sh
# Crea los roles y la BD según ADR-002. Se ejecuta solo al inicializar el volumen.
#   crm_migrator: propietario del esquema, ejecuta migraciones (BYPASSRLS para migraciones de datos).
#   crm_app:      runtime; NO propietario, NO superusuario, NO BYPASSRLS; solo DML.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
  -v db="$CRM_DB_NAME" \
  -v migrator_pw="$CRM_MIGRATOR_PASSWORD" \
  -v app_pw="$CRM_APP_PASSWORD" <<'EOSQL'
CREATE ROLE crm_migrator LOGIN CREATEDB BYPASSRLS PASSWORD :'migrator_pw';
CREATE ROLE crm_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD :'app_pw';

CREATE DATABASE :"db" OWNER crm_migrator;
REVOKE ALL ON DATABASE :"db" FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE :"db" TO crm_app;

\connect :"db"

ALTER SCHEMA public OWNER TO crm_migrator;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO crm_app;

-- Todo objeto que cree crm_migrator será accesible (solo DML) por crm_app.
ALTER DEFAULT PRIVILEGES FOR ROLE crm_migrator IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO crm_app;
ALTER DEFAULT PRIVILEGES FOR ROLE crm_migrator IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO crm_app;
EOSQL
