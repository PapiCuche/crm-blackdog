"""Outbox transaccional: `emit` en la transacción del `tenant_scope` activo y handlers
`@tenant_task` suscritos por tipo de evento. Contrato: docs/architecture/outbox-audit.md.
"""

import json
import re
from collections.abc import Callable, Mapping
from typing import Any, TypeVar
from uuid import UUID

from django.core.serializers.json import DjangoJSONEncoder

from core.ids import new_id
from core.tenancy.context import TenantContext
from core.tenancy.scope import require_scope

NAME = re.compile(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*){1,3}")  # fullmatch: "modulo.evento"
TYPE = re.compile(r"[a-z][a-z0-9_]{0,49}")
MAX_PAYLOAD = 16_384
T = TypeVar("T")
_SUBSCRIBERS: dict[str, list[Any]] = {}


def _check(pattern: re.Pattern[str], value: str, what: str) -> None:
    if not pattern.fullmatch(value):
        raise ValueError(f"{what} inválido: {value!r}")


def emit(
    ctx: TenantContext,
    event_type: str,
    *,
    aggregate_type: str,
    aggregate_id: UUID,
    payload: Mapping[str, Any] | None = None,
) -> UUID:
    from core.outbox.models import OutboxEvent

    alias = require_scope(ctx)
    _check(NAME, event_type, "event_type")
    _check(TYPE, aggregate_type, "aggregate_type")
    data = dict(payload or {})
    if len(json.dumps(data, cls=DjangoJSONEncoder)) > MAX_PAYLOAD:
        raise ValueError(f"payload de {event_type} supera {MAX_PAYLOAD} bytes")
    event_id = new_id()
    OutboxEvent.objects.using(alias).create(
        id=event_id,
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=data,
        correlation_id=ctx.correlation_id,
    )
    return event_id


def subscribe(*event_types: str) -> Callable[[T], T]:
    for event_type in event_types:
        _check(NAME, event_type, "event_type")

    def register(task: T) -> T:
        if getattr(task, "tenancy", None) != "tenant":
            raise TypeError("Solo un @tenant_task puede suscribirse a eventos del outbox")
        for event_type in event_types:
            handlers = _SUBSCRIBERS.setdefault(event_type, [])
            if all(h.name != task.name for h in handlers):  # type: ignore[attr-defined]
                handlers.append(task)
        return task

    return register


def handlers_for(event_type: str) -> tuple[Any, ...]:
    return tuple(_SUBSCRIBERS.get(event_type, ()))
