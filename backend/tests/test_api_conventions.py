"""F2-12 (ADR-014 §1 y §3): un solo cuerpo de error en toda la API, venga de donde venga."""

from typing import Any
from uuid import uuid4

import pytest
from django.db import connection
from django.http import Http404, HttpResponse, HttpResponseNotAllowed, StreamingHttpResponse
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import path, re_path
from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, generics, serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import Entity, record
from core import outbox
from core.api.errors import ApiError
from core.api.middleware import API_CSP
from core.api.schema import errors
from tests import test_access_api, test_authorization
from tests.tenancy_app.models import Widget
from tests.test_access_api import MANAGE, TENANT, WidgetDetail, WidgetList, detail, url
from tests.test_authorization import VIEW, give

api, world = test_access_api.api, test_authorization.world  # fixtures de F2-05A y F2-05B

pytestmark = [pytest.mark.usefixtures("tenant_db"), pytest.mark.urls(__name__)]
NOT_FOUND = (404, b'{"code":"NOT_FOUND"}')


class NoteSerializer(serializers.Serializer[Any]):
    title = serializers.CharField(max_length=5)
    size = serializers.IntegerField()

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["size"] > 9:
            raise serializers.ValidationError("demasiado grande", code="too_big")
        return attrs


class Notes(generics.GenericAPIView[Any]):
    """Ruta de plataforma que valida, falla y lanza un error de dominio."""

    permission_classes = [AllowAny]
    serializer_class = NoteSerializer

    def get(self, request: Any) -> Response:
        return Response({"ok": True})

    def post(self, request: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data["title"] == "boom":
            raise RuntimeError("SELECT * FROM users; password=hunter2")
        if serializer.validated_data["title"] == "last":
            raise ApiError("LAST_OWNER", 409, "Debe quedar un Owner activo.")
        return Response({"ok": True}, status=201)


class ItemSerializer(serializers.Serializer[Any]):
    name = serializers.CharField(max_length=3)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["name"] == "bad":
            raise serializers.ValidationError("fila inválida", code="row_bad")
        return attrs


class OrderSerializer(serializers.Serializer[Any]):
    customer = ItemSerializer()
    items = ItemSerializer(many=True)


class Orders(Notes):
    serializer_class = OrderSerializer


class Writes(APIView):
    """Vista de tenant que escribe (fila, evento y auditoría) y después falla."""

    required_permissions = {"POST": MANAGE}
    FAILURES: dict[str, Exception] = {
        "domain": ApiError("LAST_OWNER", 409),
        "invalid": serializers.ValidationError({"name": "mal"}),
        "missing": Http404(),
        "crash": RuntimeError("fallo inesperado"),
    }

    def post(self, request: Any, case: str, **kwargs: Any) -> Response:
        tenant = request._request.tenant
        widget = Widget.objects.create(name=f"escrito-{case}")
        outbox.emit(tenant, "widget.created", aggregate_type="widget", aggregate_id=widget.pk)
        record(tenant, "widget.created", Entity("widget", widget.pk))
        if case in self.FAILURES:
            raise self.FAILURES[case]
        return Response({"id": str(widget.pk)}, status=201)


class Odd(Notes):
    """Respuestas y errores poco comunes: cada uno debe salir con el contrato."""

    CASES: dict[str, Exception] = {
        "conflict": exceptions.APIException("ocupado"),
        "anonymous": exceptions.NotAuthenticated(),
        "leaf": serializers.ValidationError({"email": "mal"}),
        "both": serializers.ValidationError({"non_field_errors": ["g"], "_": ["u"]}),
        "nocode": serializers.ValidationError({"f": [exceptions.ErrorDetail("sin código")]}),
    }
    reached: list[str] = []

    def get(self, request: Any, case: str = "", **kwargs: Any) -> Response:
        self.reached.append(case)
        if case == "bare":
            return Response(status=409)  # sin cuerpo: DRF no le pone Content-Type
        error = self.CASES[case]
        if case == "conflict":
            error.status_code = 409  # type: ignore[attr-defined]
        raise error


def not_allowed(request: Any) -> HttpResponseNotAllowed:
    return HttpResponseNotAllowed(["GET"])  # una respuesta de Django, en HTML


def html(request: Any, kind: str) -> Any:
    if kind == "stream":
        response: Any = StreamingHttpResponse(iter(["<h1>", "error", "</h1>"]), status=500)
    else:  # otro juego de caracteres y cabeceras del cuerpo original
        response = HttpResponse("mal", status=400, content_type="text/html; charset=utf-16")
        response.headers["Content-Encoding"] = "gzip"
        response.headers["ETag"] = '"abc"'
    response.headers["X-Keep"] = "1"
    response.set_cookie("visto", "1")
    return response


urlpatterns = [
    path(TENANT + "widgets/", WidgetList.as_view()),
    path(TENANT + "widgets/<uuid:pk>/", WidgetDetail.as_view()),
    path(TENANT + "writes/<str:case>/", Writes.as_view()),
    path("api/v1/notes/", Notes.as_view()),
    path("api/v1/orders/", Orders.as_view()),
    path("api/v1/plain/", not_allowed),
    path("api/v1/html/<str:kind>/", html),
    path("api/v1/odd/<str:case>/", Odd.as_view()),
    # Una ruta de tenant más laxa que el middleware: acepta slugs que este no resuelve.
    re_path(r"^api/v1/o/(?P<org_slug>[^/]+)/lax/$", Odd.as_view(), {"case": "bare"}),
]


def reply(response: Any) -> tuple[int, bytes]:
    return response.status_code, response.content


def post(client: Client, target: str, body: Any = None, headers: Any = None) -> Any:
    return client.post(target, body or {}, content_type="application/json", headers=headers)


def test_drf_errors_use_the_contract_body(api: Any) -> None:
    assert reply(api.client.get(url())) == (403, b'{"code":"PERMISSION_DENIED"}')  # sin roles
    assert reply(api.client.put("/api/v1/notes/")) == (405, b'{"code":"METHOD_NOT_ALLOWED"}')
    broken = api.client.post("/api/v1/notes/", "{no json", content_type="application/json")
    assert reply(broken) == (400, b'{"code":"PARSE_ERROR"}')
    xml = api.client.post("/api/v1/notes/", "<a/>", content_type="application/xml")
    assert reply(xml) == (415, b'{"code":"UNSUPPORTED_MEDIA_TYPE"}')
    not_acceptable = api.client.get("/api/v1/notes/", HTTP_ACCEPT="application/xml")
    assert reply(not_acceptable) == (406, b'{"code":"NOT_ACCEPTABLE"}')
    assert api.client.get("/api/v1/notes/?format=xml").json() == {"ok": True}  # sin `?format=`


def test_validation_errors_list_fields_with_stable_codes(api: Any) -> None:
    response = post(api.client, "/api/v1/notes/", {"title": "demasiado"})
    assert response.status_code == 400
    assert set(response.json()) == {"code", "fields"}
    fields = response.json()["fields"]
    codes = {name: [error["code"] for error in found] for name, found in fields.items()}
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert codes == {"title": ["max_length"], "size": ["required"]}  # códigos estables
    assert all(error["message"] for found in fields.values() for error in found)
    whole = post(api.client, "/api/v1/notes/", {"title": "ok", "size": 10}).json()
    assert whole["fields"] == {"_": [{"code": "too_big", "message": "demasiado grande"}]}
    domain = post(api.client, "/api/v1/notes/", {"title": "last", "size": 1})
    assert domain.status_code == 409
    assert domain.json() == {"code": "LAST_OWNER", "message": "Debe quedar un Owner activo."}


def test_nested_and_listed_validation_errors_keep_the_contract_shape(api: Any) -> None:
    body = {"customer": {"name": "bad"}, "items": [{"name": "ok"}, {"name": "largo"}, {}]}
    fields = post(api.client, "/api/v1/orders/", body).json()["fields"]

    def codes(node: Any) -> Any:
        if isinstance(node, list):
            assert all(set(error) == {"code", "message"} and error["message"] for error in node)
            return [error["code"] for error in node]
        return {key: codes(value) for key, value in node.items()}

    assert codes(fields) == {
        "customer": {"_": ["row_bad"]},  # error general de un serializador anidado
        "items": {"1": {"name": ["max_length"]}, "2": {"name": ["required"]}},  # por índice
    }
    assert "non_field_errors" not in str(fields)  # el nombre de DRF no sale a ningún nivel


def test_every_tenant_404_is_the_same_document(api: Any) -> None:
    give(api.a, api.membership, {VIEW: "OWN", MANAGE: "OWN"})
    targets = (
        url(org="no-existe"),  # la organización no existe (middleware)
        url(org="org-b"),  # sin membresía (middleware)
        detail(uuid4()),  # objeto inexistente (DRF)
        detail(api.theirs),  # fuera de su alcance (DRF)
        detail(api.orgs["widget_B"]),  # de otra organización (DRF)
        url("no-hay-ruta/"),  # ruta sin resolver, siendo miembro (Django)
        "/api/v1/o/no-existe/no-hay-ruta/",
        url("widgets"),  # sin la barra final: no hay redirección
        url("widgets", org="org-b"),
    )
    assert {reply(api.client.get(target)) for target in targets} == {NOT_FOUND}
    for slug in ("a.b", "con espacio", "ñandú"):  # un slug imposible nunca llega a una vista
        assert reply(api.client.get(f"/api/v1/o/{slug}/widgets/")) == NOT_FOUND
    assert reply(api.client.get("/api/v1/nada/")) == NOT_FOUND  # también fuera de un tenant
    assert reply(Client().get("/api/nada")) == NOT_FOUND
    unauthenticated = Client().get(url())
    assert reply(unauthenticated) == (401, b'{"code":"NOT_AUTHENTICATED"}')
    assert unauthenticated.headers["WWW-Authenticate"] == "Session"


@pytest.mark.parametrize("debug", [False, True])
def test_errors_from_outside_a_view_never_leak_detail(api: Any, settings: Any, debug: bool) -> None:
    settings.DEBUG = debug  # la página técnica de Django tampoco sale por la API
    client = Client(raise_request_exception=False)
    crash = post(client, "/api/v1/notes/", {"title": "boom", "size": 1})
    assert reply(crash) == (500, b'{"code":"INTERNAL_ERROR"}')
    assert reply(client.get("/api/v1/nada/")) == NOT_FOUND
    host = client.get("/api/v1/notes/", headers={"Host": "evil.example"})  # DisallowedHost
    assert reply(host) == (400, b'{"code":"BAD_REQUEST"}')
    assert host.headers["Content-Security-Policy"] == API_CSP
    for target in ("/api/v1/notes", url("widgets")):  # sin la barra final
        assert reply(api.client.get(target)) == NOT_FOUND
        assert reply(api.client.post(target)) == NOT_FOUND
    plain = api.client.post("/api/v1/plain/")  # respuesta HTML de una vista de Django
    assert reply(plain) == (405, b'{"code":"METHOD_NOT_ALLOWED"}')
    assert plain.headers["Allow"] == "GET"  # las cabeceras de protocolo se conservan
    assert plain.headers["Content-Length"] == str(len(plain.content))
    outside = client.get("/health/nada")  # fuera de /api/ no se toca
    assert outside.status_code == 404 and "text/html" in outside.headers["Content-Type"]
    assert "Content-Security-Policy" not in outside.headers


@pytest.mark.parametrize("case", ["domain", "invalid", "missing", "crash"])
def test_a_tenant_request_that_ends_in_error_writes_nothing(
    api: Any, migrator: Any, case: str
) -> None:
    give(api.a, api.membership, {MANAGE: "ORGANIZATION"})
    client = Client(raise_request_exception=False)
    client.force_login(api.ana)

    def written() -> tuple[int, ...]:
        tables = ("tenancy_app_widget", "outbox_events", "audit_logs")
        return tuple(
            migrator.execute(f"SELECT count(*) FROM {t}").fetchone()[0]  # noqa: S608
            for t in tables
        )

    before = written()
    failed = client.post(url(f"writes/{case}/"))
    assert failed.status_code >= 400 and "code" in failed.json()
    assert written() == before  # ni la fila, ni el evento, ni la auditoría
    assert client.post(url("writes/ok/")).status_code == 201
    assert written() == tuple(n + 1 for n in before)  # sin error, las tres


def test_error_component_is_part_of_the_contract() -> None:
    @extend_schema(responses={200: OpenApiTypes.OBJECT, **errors(401, 404)})
    class Documented(Notes):
        """Vista documentada con el componente común."""

    generator = SchemaGenerator(patterns=[path("api/v1/documented/", Documented.as_view())])
    schema = generator.get_schema(request=None, public=True)
    responses = schema["paths"]["/api/v1/documented/"]["get"]["responses"]
    ref = {"$ref": "#/components/schemas/Error"}
    assert responses["401"]["content"]["application/json"]["schema"] == ref
    assert responses["404"]["content"]["application/json"]["schema"] == ref
    error = schema["components"]["schemas"]["Error"]
    assert error["required"] == ["code"] and set(error["properties"]) == {
        "code",
        "message",
        "fields",
    }


def test_api_responses_carry_a_closed_csp(api: Any) -> None:
    for response in (
        api.client.get("/api/v1/notes/"),
        api.client.get("/api/v1/nada/"),
        api.client.get(url()),
        Client().get(url()),
    ):
        assert response.headers["Content-Security-Policy"] == API_CSP
    assert "Content-Security-Policy" not in Client().get("/health/live").headers


def test_membership_is_looked_up_whether_or_not_the_organization_exists(api: Any) -> None:
    def work(org: str) -> list[str]:
        with CaptureQueriesContext(connection) as queries:
            assert reply(api.client.get(url(org=org))) == NOT_FOUND
        return [query["sql"].split(" WHERE ")[0] for query in queries]

    missing, foreign = work("no-existe"), work("org-b")
    assert missing == foreign  # mismo trabajo: el tiempo no delata qué slugs existen
    assert any("organization_memberships" in sql for sql in missing)


def test_unusual_errors_also_follow_the_contract(api: Any) -> None:
    def odd(case: str) -> Any:
        return api.client.get(f"/api/v1/odd/{case}/")

    for case in ("bare", "conflict"):  # un 4xx sin código propio no es un error del servidor
        assert reply(odd(case)) == (409, b'{"code":"ERROR"}')
    anonymous = odd("anonymous")  # sin sesión es 401, tenga o no la vista autenticación
    assert reply(anonymous) == (401, b'{"code":"NOT_AUTHENTICATED"}')
    assert anonymous.headers["WWW-Authenticate"] == "Session"
    assert odd("leaf").json()["fields"] == {"email": [{"code": "invalid", "message": "mal"}]}
    both = odd("both").json()["fields"]
    assert [error["message"] for error in both["_"]] == ["g", "u"]  # se unen, no se pisan
    assert odd("nocode").json()["fields"] == {"f": [{"code": "invalid", "message": "sin código"}]}


def test_a_slug_the_middleware_cannot_resolve_never_reaches_a_view(api: Any) -> None:
    Odd.reached.clear()
    for slug in ("a.b", "con%20espacio", "%C3%B1and%C3%BA"):
        assert reply(api.client.get(f"/api/v1/o/{slug}/lax/")) == NOT_FOUND
    assert Odd.reached == []  # la ruta la aceptaría; el middleware responde antes


def test_html_errors_are_rewritten_with_clean_headers(api: Any) -> None:
    client = Client(raise_request_exception=False)
    for kind, status, code in (("stream", 500, "INTERNAL_ERROR"), ("utf16", 400, "BAD_REQUEST")):
        response = client.get(f"/api/v1/html/{kind}/")
        assert reply(response) == (status, f'{{"code":"{code}"}}'.encode())  # UTF-8, no UTF-16
        assert response.headers["Content-Type"] == "application/json"
        assert response.headers["Content-Length"] == str(len(response.content))
        assert response.headers["X-Keep"] == "1" and response.cookies["visto"].value == "1"
        for stale in ("Content-Encoding", "ETag"):
            assert stale not in response.headers
    assert reply(client.get("/api")) == NOT_FOUND  # `/api` a secas también es de la API
    assert client.get("/api").headers["Content-Security-Policy"] == API_CSP
