"""Acceso por sesión (F2-03A; ADR-003 §2, ADR-013 §5, ADR-014 §3).

`login` es una operación de plataforma: ocurre antes de elegir organización, no abre
`tenant_scope` y se audita en `platform_audit_logs`.
"""

import ipaddress
import logging
from typing import Any

from django.contrib.auth import SESSION_KEY, authenticate
from django.contrib.auth import login as django_login
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpRequest

from apps.accounts.emails import canonical_email
from apps.accounts.models import User
from apps.audit import platform
from apps.audit.services import Entity, Result
from core.api.errors import ApiError
from core.observability import reporting

logger = logging.getLogger(__name__)
INVALID_CREDENTIALS = "INVALID_CREDENTIALS"


def _client(request: HttpRequest) -> dict[str, Any]:
    """IP y agente del cliente. La IP es la que resuelve el servidor ASGI desde los proxies de
    confianza (`FORWARDED_ALLOW_IPS`); nunca una cabecera leída aquí."""
    remote = request.META.get("REMOTE_ADDR") or ""
    try:
        ipaddress.ip_address(remote)  # lo mismo que valida la auditoría: una IP rara no la rompe
    except ValueError:
        remote = ""
    return {"ip": remote or None, "user_agent": request.META.get("HTTP_USER_AGENT")}


def _audit_failure(email: str, client: dict[str, Any]) -> None:
    """El motivo real solo queda en la auditoría; al cliente le llega siempre lo mismo."""
    try:
        try:
            identifier = canonical_email(email)
            account = User.objects.filter(email=identifier).only("id", "is_active").first()
        except ValidationError:
            identifier, account = email, None
        if account is None:
            reason = "unknown_identifier"
        else:
            reason = "wrong_password" if account.is_active else "inactive_user"
        platform.record(
            "auth.login.failed",
            actor_type=platform.Actor.ANONYMOUS,
            identifier=identifier,
            entity=Entity("user", account.pk) if account else None,
            metadata={"reason": reason},
            result=Result.FAILED,
            **client,
        )
    except Exception as error:  # nada de la auditoría cambia la respuesta de un acceso rechazado
        logger.exception("auth.login.failed sin auditar")
        try:  # ADR-013 §5: también al reporte de errores; solo la acción, nunca el identificador
            reporting.reporter().capture_exception(error, {"action": "auth.login.failed"})
        except Exception:
            logger.exception("auth.login.failed: no se pudo reportar")


def login(request: HttpRequest, *, email: str, password: str) -> User:
    """Autentica y abre la sesión. La misma respuesta para un email desconocido, una contraseña
    incorrecta y un usuario desactivado. Si el acceso no se puede auditar, no hay sesión."""
    client = _client(request)
    user = authenticate(request, username=email, password=password)
    if user is None:
        _audit_failure(email, client)
        raise ApiError(INVALID_CREDENTIALS, 401)
    assert isinstance(user, User)  # noqa: S101 — el único backend es ModelBackend
    with transaction.atomic():
        if SESSION_KEY in request.session:  # ya autenticada: `django_login` conservaría su ID
            request.session.clear()  # vacía: la clave nueva se crea antes de borrar la anterior
        django_login(request, user)  # rota el ID de sesión y el token CSRF
        platform.record(
            "auth.login.succeeded", actor_type=platform.Actor.USER, actor_id=user.pk, **client
        )
    return user
