"""Comprobaciones defensivas del rol de runtime (ADR-002 §1.1).

El guard por presencia de credenciales del migrador vive en `config/settings/production.py`
(F1-02). Aquí se añaden las comprobaciones sobre el rol realmente conectado.
"""

from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.db.backends.base.base import BaseDatabaseWrapper

_ROLE = "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
_OWNED = (
    "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
    "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p') AND c.relowner = "
    "(SELECT oid FROM pg_roles WHERE rolname = current_user)"
)


def runtime_role_problems(connection: BaseDatabaseWrapper) -> list[str]:
    with connection.cursor() as cursor:
        cursor.execute(_ROLE)
        rolsuper, rolbypassrls = cursor.fetchone() or (True, True)
        cursor.execute(_OWNED)
        (owned,) = cursor.fetchone() or (0,)
    problems = []
    if rolsuper:
        problems.append("el rol conectado es superusuario")
    if rolbypassrls:
        problems.append("el rol conectado tiene BYPASSRLS")
    if owned:
        problems.append(f"el rol conectado es propietario de {owned} tablas")
    return problems


def enforce_runtime_role(sender: Any, connection: BaseDatabaseWrapper, **kwargs: Any) -> None:
    """Receptor de `connection_created`: cada conexión nueva del runtime se verifica."""
    problems = runtime_role_problems(connection)
    if problems:
        connection.close()
        raise ImproperlyConfigured("Rol de BD no apto para el runtime: " + "; ".join(problems))
