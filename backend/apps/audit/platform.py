"""Auditoría de plataforma (ADR-013): eventos que no pertenecen a ninguna organización.

`record()` solo inserta en `platform_audit_logs`. No recibe tenant: falla si hay un
`tenant_scope` activo, donde lo que corresponde es `apps.audit.services.record`. Escribe en la
transacción del llamador, si la hay, dentro de un savepoint: si la inserción falla, lanza el
error y la transacción del llamador sigue utilizable. Quien no lo captura la deshace entera:
lo auditado no ocurre sin su registro.
"""

import ipaddress
import json
import re
from collections.abc import Mapping
from enum import StrEnum
from typing import Any
from uuid import UUID

from django.core.serializers.json import DjangoJSONEncoder
from django.db import connections, transaction
from django.utils.crypto import salted_hmac

from apps.audit.services import Entity, Result
from core.ids import new_id
from core.observability.context import current_correlation_id, current_request_id
from core.outbox import NAME, TYPE
from core.redaction import redact, redact_text
from core.tenancy.context import require_no_tenant

ACTION_MAX = 100
USER_AGENT_MAX = 512
METADATA_MAX = 4096  # bytes del JSON: los metadatos son de quien llama, nunca texto del cliente
EMAIL_MASK = "[EMAIL]"
# Cualquier cosa con forma de dirección, en cualquier alfabeto, con `@` o `%40`. Anclada por la
# izquierda: una cadena larga sin `@` se recorre una sola vez.
_LOCAL = r"[^\s<>()\[\]{},;:\"=@]"
EMAIL = re.compile(
    rf"(?i)(?:(?<!{_LOCAL}){_LOCAL}+?|\"[^\"\n]{{1,64}}\"|(?<=\[REDACTED\]))"
    rf"(?:@|%40)(?:\[[^\]\s]*\]|[^\s<>()\[\]{{}},;:\"'@]+)"
)
_HASH_SALT = "apps.audit.platform.identifier"
_INSERT = (  # esquema explícito: una tabla temporal con el mismo nombre no captura la fila
    "INSERT INTO public.platform_audit_logs (id, occurred_at, actor_type, actor_id, "
    "identifier_hash, action, entity_type, entity_id, metadata, ip, user_agent, request_id, "
    "correlation_id, result) "
    "VALUES (%s, now(), %s, %s, %s, %s, %s, %s, %s::jsonb, %s::inet, %s, %s, %s, %s)"
)


class Actor(StrEnum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    PLATFORM_STAFF = "PLATFORM_STAFF"
    ANONYMOUS = "ANONYMOUS"


def identifier_hash(identifier: str) -> str:
    """Huella HMAC-SHA-256 de un identificador de acceso (email canónico). No es reversible con
    solo la BD y cambia si rota `SECRET_KEY` (ADR-013 §4). El identificador nunca se guarda."""
    normalized = identifier.strip().lower()
    return salted_hmac(_HASH_SALT, normalized, algorithm="sha256").hexdigest()


def _mask(value: Any) -> Any:
    """Además del redactor compartido, este registro no guarda direcciones de email (§4)."""
    if isinstance(value, str):
        return EMAIL.sub(EMAIL_MASK, value)
    if isinstance(value, dict):
        masked = {_mask(key): _mask(item) for key, item in value.items()}
        if len(masked) != len(value):  # dos claves distintas no se funden en una
            raise ValueError("metadata: claves con forma de email")
        return masked
    if isinstance(value, list):
        return [_mask(item) for item in value]
    return value


def _address(ip: str | None) -> str | None:
    """Una dirección que PostgreSQL acepta como `inet`, sin zona y sin forma IPv4-en-IPv6."""
    if ip is None or ip == "":
        return None
    if not isinstance(ip, str):
        raise ValueError("ip debe ser texto")
    address = ipaddress.ip_address(ip)
    if isinstance(address, ipaddress.IPv6Address):
        address = address.ipv4_mapped or ipaddress.IPv6Address(int(address))  # quita `%zona`
    return str(address)


def _metadata(metadata: Mapping[str, Any] | None) -> str:
    raw = dict(metadata or {})
    # Antes de redactar: acota el coste de las expresiones regulares sobre una entrada enorme.
    if len(json.dumps(raw, cls=DjangoJSONEncoder, allow_nan=False)) > 8 * METADATA_MAX:
        raise ValueError(f"metadata supera {METADATA_MAX} bytes")
    payload = json.dumps(_mask(redact(raw)), cls=DjangoJSONEncoder, allow_nan=False)
    if len(payload.encode()) > METADATA_MAX:
        raise ValueError(f"metadata supera {METADATA_MAX} bytes")
    if "\\u0000" in payload:
        raise ValueError("metadata contiene un carácter nulo")
    return payload


def record(
    action: str,
    *,
    actor_type: Actor,
    actor_id: UUID | None = None,
    identifier: str | None = None,
    entity: Entity | None = None,
    metadata: Mapping[str, Any] | None = None,
    result: Result = Result.SUCCESS,
    ip: str | None = None,
    user_agent: str | None = None,
) -> UUID:
    """`action = "dominio.entidad.verbo"` (p. ej., auth.login.failed). `identifier` es el email
    presentado: se guarda solo su huella. `ip` debe ser una dirección válida o `None`."""
    require_no_tenant("La auditoría de plataforma")
    if not NAME.fullmatch(action) or len(action) > ACTION_MAX:
        raise ValueError(f"action inválida: {action!r}")
    if entity is not None and not TYPE.fullmatch(entity.type):
        raise ValueError(f"entity.type inválido: {entity.type!r}")
    actor_type = Actor(actor_type)
    if actor_type is Actor.ANONYMOUS and actor_id is not None:
        raise ValueError("un actor ANONYMOUS no lleva actor_id")
    if actor_type is Actor.USER and actor_id is None:
        raise ValueError("un actor USER lleva actor_id")
    if user_agent:  # se acota antes de aplicar expresiones regulares a texto del cliente
        user_agent = user_agent.replace("\x00", "")[: 4 * USER_AGENT_MAX]
        user_agent = _mask(redact_text(user_agent))[:USER_AGENT_MAX]
    audit_id = new_id()
    values: list[Any] = [
        audit_id,
        actor_type,
        actor_id,
        identifier_hash(identifier) if identifier and identifier.strip() else None,
        action,
        entity.type if entity else None,
        entity.id if entity else None,
        _metadata(metadata),
        _address(ip),
        user_agent or None,
        current_request_id(),
        current_correlation_id(),
        Result(result),
    ]
    with transaction.atomic(), connections["default"].cursor() as cursor:
        cursor.execute(_INSERT, values)
    return audit_id
