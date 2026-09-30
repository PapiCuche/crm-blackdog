"""Contexto de observabilidad: `request_id` (una petición HTTP) y `correlation_id` (cadena de
trabajo entre procesos). Fuente de verdad propia: structlog lo consume, no lo posee.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
Tokens = tuple[Token[str | None], Token[str | None]]


def current_request_id() -> str | None:
    return _request_id.get()


def current_correlation_id() -> str | None:
    return _correlation_id.get()


def bind(*, request_id: str | None, correlation_id: str | None) -> Tokens:
    """Fija AMBOS valores (un `None` también oculta el anterior). Deshacer con `reset()`."""
    return _request_id.set(request_id), _correlation_id.set(correlation_id)


def reset(tokens: Tokens) -> None:
    _request_id.reset(tokens[0])
    _correlation_id.reset(tokens[1])


@contextmanager
def bound(*, request_id: str | None, correlation_id: str | None) -> Iterator[None]:
    tokens = bind(request_id=request_id, correlation_id=correlation_id)
    try:
        yield
    finally:
        reset(tokens)
