"""Auditoría de plataforma (ADR-013): eventos que no pertenecen a ninguna organización.

`record()` solo inserta en `platform_audit_logs`. No recibe tenant: falla si hay un
`tenant_scope` activo, donde lo que corresponde es `apps.audit.services.record`. Escribe en la
transacción del llamador, si la hay, y deja propagar el error si la inserción falla: lo
auditado no ocurre sin su registro.
"""

import ipaddress
import json
import re
from collections.abc import Mapping
from enum import StrEnum
from typing import Any
from uuid import UUID

from django.core.serializers.json import DjangoJSONEncoder
from django.db import connections
from django.utils.crypto import salted_hmac

from apps.audit.services import Entity, Result
from core.ids import new_id
from core.observability.context import current_correlation_id, current_request_id
from core.outbox import NAME, TYPE
from core.redaction import redact, redact_text
from core.tenancy.context import require_no_tenant

USER_AGENT_MAX = 512
METADATA_MAX = 4096  # bytes del JSON: los metadatos son de quien llama, nunca texto del cliente
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
EMAIL_MASK = "[EMAIL]"
_HASH_SALT = "apps.audit.platform.identifier"
_INSERT = (
    "INSERT INTO platform_audit_logs (id, occurred_at, actor_type, actor_id, identifier_hash, "
    "action, entity_type, entity_id, metadata, ip, user_agent, request_id, correlation_id, "
    "result) VALUES (%s, now(), %s, %s, %s, %s, %s, %s, %s::jsonb, %s::inet, %s, %s, %s, %s)"
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
        return {_mask(k): _mask(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_mask(item) for item in value]
    return value


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
    if not NAME.fullmatch(action):
        raise ValueError(f"action inválida: {action!r}")
    if entity is not None and not TYPE.fullmatch(entity.type):
        raise ValueError(f"entity.type inválido: {entity.type!r}")
    actor_type = Actor(actor_type)
    if actor_type is Actor.ANONYMOUS and actor_id is not None:
        raise ValueError("un actor ANONYMOUS no lleva actor_id")
    address = str(ipaddress.ip_address(ip)) if ip else None
    payload = json.dumps(_mask(redact(dict(metadata or {}))), cls=DjangoJSONEncoder)
    if len(payload.encode()) > METADATA_MAX:
        raise ValueError(f"metadata supera {METADATA_MAX} bytes")
    audit_id = new_id()
    with connections["default"].cursor() as cursor:
        cursor.execute(
            _INSERT,
            [
                audit_id,
                actor_type,
                actor_id,
                identifier_hash(identifier) if identifier else None,
                action,
                entity.type if entity else None,
                entity.id if entity else None,
                payload,
                address,
                _mask(redact_text(user_agent))[:USER_AGENT_MAX] if user_agent else None,
                current_request_id(),
                current_correlation_id(),
                Result(result),
            ],
        )
    return audit_id
