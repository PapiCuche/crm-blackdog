"""Componente `Error` del contrato OpenAPI (ADR-014 §1): el cuerpo de toda respuesta de error."""

from typing import Any

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

ERROR = inline_serializer(
    name="Error",
    fields={
        "code": serializers.CharField(help_text="Código estable. Lo único que decide el cliente."),
        "message": serializers.CharField(required=False, help_text="Texto seguro para mostrar."),
        "fields": serializers.DictField(
            required=False,
            help_text="Solo en VALIDATION_ERROR: errores por campo (`_`: generales).",
        ),
    },
)


class SessionScheme(OpenApiAuthenticationExtension):  # type: ignore[misc]
    """La sesión de Django en el contrato: una cookie HttpOnly que el navegador envía solo."""

    target_class = "core.api.authentication.SessionAuthentication"
    name = "sessionCookie"

    def get_security_definition(self, auto_schema: Any) -> dict[str, str]:
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": "crm_session",
            "description": "Cookie de sesión (`__Host-crm_session` en producción). Los métodos "
            "no seguros llevan además la cabecera `X-CSRFToken`.",
        }


def errors(*statuses: int) -> dict[int, Any]:
    """Para `@extend_schema(responses={200: …, **errors(400, 401)})`."""
    return dict.fromkeys(statuses, ERROR)
