"""Ruta de tenant del contexto propio (`/api/v1/o/{slug}/me/`, F2-11)."""

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.catalog import Scope
from apps.access.permissions import IsMember, request_context
from apps.access.selectors import organization_of, role_names
from core.api.schema import errors


class MemberUserSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    email = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()


class MemberOrganizationSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    slug = serializers.CharField()
    name = serializers.CharField()


class RoleNameSerializer(serializers.Serializer[Any]):
    code = serializers.CharField()
    name = serializers.CharField()


class GrantSerializer(serializers.Serializer[Any]):
    code = serializers.CharField()
    scopes = serializers.ListField(
        child=serializers.ChoiceField(choices=Scope.choices),
        help_text="Alcances concedidos. Vacío si el permiso no admite alcance.",
    )


class SelfContextSerializer(serializers.Serializer[Any]):
    user = MemberUserSerializer()
    organization = MemberOrganizationSerializer()
    membership_id = serializers.UUIDField()
    roles = RoleNameSerializer(many=True, help_text="Solo para mostrar: no autorizan nada.")
    permissions = GrantSerializer(many=True)


class SelfContextView(APIView):
    """Quién es el usuario en esta organización y qué puede hacer. Informa: no autoriza. La
    interfaz lo usa para construir la navegación; cada ruta sigue comprobando su permiso."""

    permission_classes = [IsMember]

    @extend_schema(
        operation_id="me_context",
        tags=["me"],
        responses={200: SelfContextSerializer, **errors(401, 403, 404)},
    )
    def get(self, request: Request, **kwargs: Any) -> Response:
        ectx = request_context(request)
        assert ectx is not None  # noqa: S101 — `IsMember` ya lo comprobó
        grants = [
            {"code": code, "scopes": sorted(scope for scope in scopes if scope is not None)}
            for code, scopes in sorted(ectx.permissions.items())
        ]
        payload = {
            "user": request.user,
            "organization": organization_of(ectx),
            "membership_id": ectx.membership_id,
            "roles": role_names(ectx),
            "permissions": grants,
        }
        return Response(SelfContextSerializer(payload).data)
