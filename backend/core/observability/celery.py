"""Correlación HTTP → Celery por cabecera de mensaje (ADR-011 §2).

- `before_task_publish`: añade `crm_correlation_id` si hay correlación activa (no el
  `request_id`: pertenece a la petición HTTP). Nombre propio: Celery ya usa `correlation_id`
  en las propiedades del mensaje para el id de la tarea.
- `task_prerun`: limpia y fija el contexto del worker; `task_postrun` lo restaura siempre, sin
  fugas entre tareas sucesivas del mismo worker (ni hacia la petición en modo eager).
"""

from typing import Any

from celery.signals import (
    before_task_publish,
    setup_logging,
    task_failure,
    task_postrun,
    task_prerun,
)

from core.observability.context import Tokens, bind, current_correlation_id, reset
from core.observability.logging import get_logger

HEADER = "crm_correlation_id"
logger = get_logger("core.celery")
_tokens: dict[str, Tokens] = {}


def inject_correlation(headers: dict[str, Any] | None = None, **kwargs: Any) -> None:
    correlation_id = current_correlation_id()
    if headers is not None and correlation_id and HEADER not in headers:
        headers[HEADER] = correlation_id


def correlation_from(request: Any) -> str | None:
    """Cabecera en el worker (protocolo 2) o en `request.headers` (modo eager, `apply()`)."""
    value = getattr(request, HEADER, None) or (getattr(request, "headers", None) or {}).get(HEADER)
    return str(value) if value else None


def bind_task(task_id: str, task: Any = None, **kwargs: Any) -> None:
    request = getattr(task, "request", None)
    correlation_id = correlation_from(request)
    if correlation_id is None and getattr(request, "is_eager", False):
        correlation_id = current_correlation_id()  # .delay() eager: no hay publish ni cabecera
    _tokens[task_id] = bind(request_id=None, correlation_id=correlation_id)


def reset_task(task_id: str, **kwargs: Any) -> None:
    tokens = _tokens.pop(task_id, None)
    if tokens is not None:
        reset(tokens)


def log_failure(task_id: str, exception: BaseException, sender: Any = None, **kw: Any) -> None:
    logger.error(
        "celery.task.failed",
        task_name=getattr(sender, "name", None),
        task_id=task_id,
        exception_type=type(exception).__name__,
    )  # nunca args/kwargs


def use_django_logging(**kwargs: Any) -> None:
    """Receptor de `setup_logging`: Celery no instala sus handlers de texto sin redactar."""


def connect() -> None:
    setup_logging.connect(use_django_logging, dispatch_uid="crm_celery_logging")
    before_task_publish.connect(inject_correlation, dispatch_uid="crm_correlation_publish")
    task_prerun.connect(bind_task, dispatch_uid="crm_correlation_prerun")
    task_postrun.connect(reset_task, dispatch_uid="crm_correlation_postrun")
    task_failure.connect(log_failure, dispatch_uid="crm_task_failure")
