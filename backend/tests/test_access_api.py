"""F2-05B: el motor de autorización en DRF. Denegación por defecto; 401, 404 y 403.

Las vistas de DRF de prueba y su URLconf viven aquí (no en `tests/urls.py`): middleware y
resolvedor reales, sesión de Django y PostgreSQL con el rol `crm_app`.
"""

import json
import re
from collections.abc import Iterator, Mapping
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from django.db import connection
from django.db.models import QuerySet
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import URLResolver, path, re_path
from django.urls.resolvers import RegexPattern
from django.views.decorators.cache import cache_page
from rest_framework import generics, serializers, viewsets
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

import config.urls
from apps.access.catalog import BY_CODE, PermissionDef
from apps.access.models import MembershipRole, Role, RolePermission
from apps.access.permissions import HasPermission, ScopeFilter
from apps.access.services import clone_role_templates
from apps.accounts.models import User
from apps.organizations.models import OrganizationMembership
from config.settings import base
from core.tenancy.middleware import TENANT_PATH
from core.tenancy.scope import tenant_scope
from tests import urls as legacy_urls
from tests.factories import TEST_PASSWORD
from tests.tenancy_app.models import Widget
from tests.test_access import NEW_PERMISSION
from tests.test_authorization import VIEW, give, world  # noqa: F401 — `world` es una fixture
from tests.test_memberships import ctx, join

pytestmark = [pytest.mark.usefixtures("tenant_db"), pytest.mark.urls(__name__)]
MANAGE = "widgets.manage"  # segundo permiso de prueba con alcance
TENANT = "api/v1/o/<slug:org_slug>/"
PLATFORM = frozenset({"api/schema/"})  # vistas de DRF de plataforma del proyecto: otra frontera
PREFIX = "api/v1/o/"  # las rutas de tenant, como `TENANT_PATH` en el middleware
DYNAMIC = re.compile(r"^.*\||.?[?*{]|[<(\[\\.+]")  # donde una ruta deja de ser texto literal
GUARDS = ("get_permissions", "check_permissions", "permission_denied", "initial", "dispatch")
HOOKS = ("get_object", "filter_queryset")  # por donde `ScopeFilter` llega al queryset


class WidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Widget
        fields = ("id", "name")
        read_only_fields = ("id",)  # la clave primaria nunca llega del cliente (OBS-F2-05B-2)


class WidgetView:
    serializer_class = WidgetSerializer

    def get_queryset(self) -> QuerySet[Widget]:
        return Widget.objects.order_by("name")


class WidgetList(WidgetView, generics.ListAPIView):
    required_permissions = {"GET": VIEW}


class WidgetDetail(WidgetView, generics.RetrieveUpdateDestroyAPIView):
    required_permissions = {"GET": VIEW, "PUT": MANAGE, "PATCH": MANAGE, "DELETE": MANAGE}


class Described(WidgetDetail):
    required_permissions = {**WidgetDetail.required_permissions, "OPTIONS": VIEW}


class Members(APIView):
    required_permissions = {"GET": "users.view"}  # permiso real del catálogo, sin alcance

    def get(self, request: Any, **kwargs: Any) -> Response:
        return Response({"ok": True})


class Open(Members):
    """Vista de plataforma: se excluye declarando sus propias clases."""

    permission_classes = [AllowAny]


class Undeclared(WidgetView, generics.ListAPIView):
    """Vista de tenant sin `required_permissions`."""


class Partial(WidgetDetail):
    required_permissions = {"GET": VIEW}  # PUT, PATCH y DELETE existen y no se declaran


class Typo(Members):
    required_permissions = {"GET": "users.vew"}


class Unfiltered(WidgetList):
    filter_backends: list[Any] = []


class Defaults(APIView):
    """Vista de DRF fuera de las rutas de tenant que no declara nada."""

    def get(self, request: Any) -> Response:
        return Response({"ok": True})


class WidgetSet(WidgetView, viewsets.ModelViewSet):
    required_permissions = {"GET": VIEW}


class OwnPermissions(Members):
    def get_permissions(self) -> list[Any]:
        return [AllowAny()]


class OwnLookup(WidgetDetail):
    def get_object(self) -> Any:
        return self.get_queryset().get(pk=self.kwargs["pk"])  # sin filter_queryset()


class OwnCheck(Members):
    def check_permissions(self, request: Any) -> None:
        """No comprueba nada."""


class Lax(HasPermission):
    def has_permission(self, request: Any, view: Any) -> bool:
        return True


secure = [
    path(TENANT + "widgets/", WidgetList.as_view()),
    path(TENANT + "widgets/<uuid:pk>/", WidgetDetail.as_view()),
    path(TENANT + "widgets/<uuid:pk>/described/", Described.as_view()),
    path(TENANT + "members/", Members.as_view()),
    path("platform/open/", Open.as_view()),
]
TENANT_RE = r"^api/v1/o/(?P<org_slug>[-\w]+)/"
FLAWED: list[tuple[Any, str]] = [  # ruta y motivo que debe dar la auditoría
    (path(TENANT + "undeclared/", Undeclared.as_view()), "sin required_permissions"),
    (path(TENANT + "widgets/<uuid:pk>/partial/", Partial.as_view()), "métodos sin permiso"),
    (path(TENANT + "set/", WidgetSet.as_view({"get": "list", "post": "create"})), "['POST']"),
    (path(TENANT + "open/", Open.as_view()), "sin HasPermission"),
    (path(TENANT + "typo/", Typo.as_view()), "fuera del catálogo"),
    (path(TENANT + "unfiltered/", Unfiltered.as_view()), "sin ScopeFilter"),
    # Lo mismo, pero por ruta (`as_view(**initkwargs)`, como hacen los routers con `@action`):
    (path(TENANT + "kw-open/", Members.as_view(permission_classes=[AllowAny])), "sin Has"),
    (
        path(TENANT + "kw-any/", Members.as_view(permission_classes=[HasPermission | AllowAny])),
        "sin Has",
    ),
    (path(TENANT + "kw-sub/", Members.as_view(permission_classes=[Lax])), "sin HasPermission"),
    (path(TENANT + "kw-bare/", Members.as_view(permission_classes=HasPermission)), "sin Has"),
    (path(TENANT + "kw-list/", Members.as_view(required_permissions={"GET": [VIEW]})), "catálogo"),
    (path(TENANT + "kw-unfiltered/", WidgetList.as_view(filter_backends=[])), "sin ScopeFilter"),
    (path(TENANT + "kw-hook/", Members.as_view(get_permissions=list)), "redefine get_permissions"),
    (path(TENANT + "kw-lookup/", WidgetDetail.as_view(get_object=dict)), "redefine get_object"),
    # Ganchos de DRF redefinidos y decoradores alrededor de `as_view()`:
    (path(TENANT + "own-permissions/", OwnPermissions.as_view()), "redefine get_permissions"),
    (path(TENANT + "own-check/", OwnCheck.as_view()), "redefine check_permissions"),
    (path(TENANT + "own-lookup/<uuid:pk>/", OwnLookup.as_view()), "redefine get_object"),
    (path(TENANT + "cached/", cache_page(300)(Members.as_view())), "decorador"),
    (path("platform/defaults/", Defaults.as_view()), "plataforma"),
    # Rutas que pueden casar con `TENANT_PATH` sin empezar por el prefijo literal:
    (path("api/<str:version>/o/<slug:org_slug>/dynamic/", Open.as_view()), "ruta dinámica"),
    (re_path(r"^apis?/v1/o/(?P<org_slug>[-\w]+)/optional/$", Open.as_view()), "ruta dinámica"),
    (re_path(r"^healthz/$|" + TENANT_RE + "either/$", Open.as_view()), "ruta dinámica"),
    (re_path(r"unanchored/", Open.as_view()), "ruta dinámica"),  # sin `^`: casa en cualquier parte
]
urlpatterns = [*secure, *(entry for entry, _ in FLAWED)]


def routes(patterns: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    for entry in patterns:
        text = str(entry.pattern)
        loose = isinstance(entry.pattern, RegexPattern) and not text.startswith("^")
        route = prefix + (".*" if loose else "") + text.lstrip("^")
        if isinstance(entry, URLResolver):
            yield from routes(entry.url_patterns, route)
        else:
            yield route, entry.callback


def insecure(patterns: Any, platform: frozenset[str]) -> dict[str, str]:
    """Auditoría del URLconf: `{ruta: motivo}` de cada ruta que no puede llegar a `main`.

    Una ruta de tenant debe ser una vista de DRF con `HasPermission`, un permiso del catálogo
    por cada método que implementa y, si es genérica, `ScopeFilter`; se mira lo que la ruta usa
    de verdad (`as_view(**initkwargs)` incluido), que no redefina los ganchos de DRF y que nada
    envuelva a `as_view()`. Una vista de DRF fuera de las rutas de tenant es de plataforma: tiene
    que figurar en `platform`, y su ruta debe apartarse de `api/v1/o/` en su parte literal, antes
    de cualquier segmento dinámico (por exceso: un router de plataforma va bajo su propio prefijo).
    Es estática: una vista que consulte por su cuenta debe usar `scoped()` (OBS-F2-05B-2).
    """
    found = dict.fromkeys(platform, "exclusión de plataforma obsoleta")
    for route, callback in routes(patterns):
        cls: Any = getattr(callback, "cls", None)
        drf = isinstance(cls, type) and issubclass(cls, APIView)
        declared = effective(callback, "required_permissions")
        literal = DYNAMIC.split(route.rstrip("$"), maxsplit=1)[0]
        if not route.startswith(PREFIX):
            if PREFIX.startswith(literal) and literal != route.rstrip("$"):
                found[route] = "ruta dinámica que puede coincidir con una ruta de tenant"
            elif drf and route in platform:
                found.pop(route, None)
            elif drf:
                found[route] = "vista de DRF de plataforma sin exclusión explícita"
        elif not drf:
            found[route] = "no es una vista de DRF"
        elif not uses(effective(callback, "permission_classes"), HasPermission):
            found[route] = "sin HasPermission"
        elif redefined := [h for h in GUARDS if effective(callback, h) is not getattr(APIView, h)]:
            found[route] = "redefine " + ", ".join(redefined)
        elif wrapped(callback):
            found[route] = "vista envuelta en un decorador"
        elif not isinstance(declared, Mapping):
            found[route] = "sin required_permissions"
        elif missing := implemented(callback) - set(declared):
            found[route] = f"métodos sin permiso: {sorted(missing)}"
        elif unknown := [
            c for c in declared.values() if not isinstance(c, str) or c not in BY_CODE
        ]:
            found[route] = f"permisos fuera del catálogo: {sorted(map(repr, unknown))}"
        elif not issubclass(cls, generics.GenericAPIView):
            continue
        elif not uses(effective(callback, "filter_backends"), ScopeFilter):
            found[route] = "sin ScopeFilter"
        elif redefined := [
            h for h in HOOKS if effective(callback, h) is not getattr(generics.GenericAPIView, h)
        ]:
            found[route] = "redefine " + ", ".join(redefined)
    return found


def effective(callback: Any, name: str) -> Any:
    """Lo que la ruta usa: `as_view(**initkwargs)` pisa el atributo de la clase."""
    kwargs = getattr(callback, "initkwargs", None) or {}
    return kwargs.get(name, getattr(getattr(callback, "cls", None), name, None))


def uses(items: Any, kind: type) -> bool:
    """`kind` figura tal cual; una subclase o una composición (`A | B`) se revisan a mano."""
    return isinstance(items, (list, tuple)) and any(item is kind for item in items)


def wrapped(callback: Any) -> bool:
    """¿Hay un decorador alrededor de `as_view()`? Respondería antes que `HasPermission`."""
    view = getattr(callback, "__wrapped__", None)  # DRF solo añade `csrf_exempt`
    dispatch = callback.cls.dispatch
    return view is None or getattr(view, "__wrapped__", dispatch) is not dispatch


def implemented(callback: Any) -> set[str]:
    """Métodos que la ruta atiende (OPTIONS y HEAD sin declarar ya se deniegan solos)."""
    names = getattr(callback, "actions", None) or [
        name for name in callback.cls.http_method_names if hasattr(callback.cls, name)
    ]
    return {name.upper() for name in names} - {"OPTIONS", "HEAD"}


def anyone(user: Any, organization_id: UUID) -> UUID:
    """Resolvedor demasiado permisivo: todo usuario pasa el middleware."""
    return user.pk  # type: ignore[no-any-return]


def url(tail: str = "widgets/", org: str = "org-a") -> str:
    return f"/api/v1/o/{org}/{tail}"


def detail(pk: UUID, tail: str = "", org: str = "org-a") -> str:
    return url(f"widgets/{pk}/{tail}", org)


def send(client: Client, method: str, target: str) -> tuple[int, bytes]:
    body = json.dumps({"name": "cambiado"})
    response = client.generic(method, target, body, content_type="application/json")
    return response.status_code, response.content


@pytest.fixture
def api(
    request: pytest.FixtureRequest,
    settings: Any,
    migrator: psycopg.Connection[Any],
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Any]:
    """El mundo de F2-05A con `widgets.manage`, dos widgets más y la sesión real de `ana`."""
    base_world = request.getfixturevalue("world")
    settings.MIDDLEWARE = base.MIDDLEWARE
    settings.TENANCY_MEMBERSHIP_RESOLVER = base.TENANCY_MEMBERSHIP_RESOLVER

    def drop() -> None:
        migrator.execute("DELETE FROM role_permissions WHERE permission_code = %s", [MANAGE])
        migrator.execute("DELETE FROM permissions WHERE code = %s", [MANAGE])

    drop()
    try:
        migrator.execute(NEW_PERMISSION, [MANAGE, True])
        monkeypatch.setitem(BY_CODE, MANAGE, PermissionDef(MANAGE, "x", supports_scope=True))
        ids = {"mine": uuid4(), "theirs": uuid4()}
        insert = "INSERT INTO tenancy_app_widget (id, organization_id, name, assigned_user_id) "
        for name, owner in (("mine", base_world.ana.pk), ("theirs", uuid4())):
            migrator.execute(
                insert + "VALUES (%s, %s, %s, %s)", [ids[name], base_world.a, name, owner]
            )
        client = Client()
        client.force_login(base_world.ana)
        yield SimpleNamespace(**vars(base_world), **ids, client=client)
    finally:
        drop()


def names(migrator: psycopg.Connection[Any]) -> list[str]:
    rows = migrator.execute("SELECT name FROM tenancy_app_widget ORDER BY name").fetchall()
    return [row[0] for row in rows]


def test_unauthenticated_is_401_and_non_member_is_404(api: Any) -> None:
    give(api.a, api.membership, {VIEW: "ORGANIZATION", MANAGE: "ORGANIZATION"})
    for target in (url(), detail(api.mine), url("undeclared/")):
        assert Client().get(target).status_code == 401  # sin sesión
    targets = (url(org="org-b"), url(org="no-existe"), detail(api.orgs["widget_B"], org="org-b"))
    replies = {send(api.client, "GET", target) for target in targets}
    assert replies == {(404, b'{"code": "NOT_FOUND"}')}  # ana no es de B: indistinguible


def test_engine_denies_what_a_lax_resolver_lets_through(api: Any, settings: Any) -> None:
    settings.TENANCY_MEMBERSHIP_RESOLVER = f"{__name__}.anyone"
    give(api.a, api.membership, {VIEW: "ORGANIZATION"})
    assert api.client.get(url()).status_code == 200
    assert api.client.get(url(org="org-b")).status_code == 404  # sin membresía en B
    assert api.client.get(url("undeclared/", org="org-b")).status_code == 404  # y no 403
    with tenant_scope(ctx(api.a)):
        OrganizationMembership.objects.update(status="SUSPENDED")
    targets = (url(), detail(api.mine), detail(uuid4()))
    replies = {send(api.client, "GET", target) for target in targets}
    assert len(replies) == 1 and replies.pop()[0] == 404  # suspendida: como si no existiera


def test_member_without_the_permission_is_403(api: Any, migrator: psycopg.Connection[Any]) -> None:
    for target in (url(), detail(api.mine), detail(uuid4()), url("members/")):
        assert api.client.get(target).status_code == 403  # miembro sin roles
    assert api.client.head(url("members/")).status_code == 403  # HEAD: el permiso de GET
    give(api.a, api.membership, {VIEW: "ORGANIZATION", "organization.view": None})
    assert api.client.get(detail(api.mine)).status_code == 200
    assert api.client.get(url("members/")).status_code == 403  # otro permiso
    for method in ("PATCH", "PUT", "DELETE"):  # cada método, su permiso: tiene `view`, no `manage`
        for pk in (api.mine, api.theirs, uuid4()):  # exista o no: la misma respuesta
            assert send(api.client, method, detail(pk))[0] == 403
    assert names(migrator) == ["mine", "theirs", "widget A", "widget B"]


def test_view_or_method_without_declaration_is_denied(
    api: Any, migrator: psycopg.Connection[Any]
) -> None:
    give(api.a, api.membership, {VIEW: "ORGANIZATION", MANAGE: "ORGANIZATION", "users.view": None})
    assert api.client.get(url("undeclared/")).status_code == 403  # vista sin declaración
    partial = detail(api.mine, "partial/")
    for method in ("PUT", "PATCH", "DELETE", "POST", "OPTIONS"):
        assert send(api.client, method, partial)[0] == 403  # método sin declarar
    assert api.client.get(partial).status_code == api.client.head(partial).status_code == 200
    assert send(api.client, "OPTIONS", detail(api.mine))[0] == 403
    assert names(migrator) == ["mine", "theirs", "widget A", "widget B"]


def test_list_returns_only_rows_in_scope_filtered_in_sql(api: Any) -> None:
    give(api.a, api.membership, {VIEW: "OWN"})
    with CaptureQueriesContext(connection) as queries:
        listed = api.client.get(url()).json()
    assert [row["name"] for row in listed] == ["mine"]
    widgets = [query["sql"] for query in queries if "tenancy_app_widget" in query["sql"]]
    assert len(widgets) == 1 and '"assigned_user_id" IN' in widgets[0]  # no se filtra en Python
    give(api.a, api.membership, {VIEW: "ORGANIZATION"})  # otro rol: los alcances se unen
    listed = api.client.get(url()).json()
    assert [row["name"] for row in listed] == ["mine", "theirs", "widget A"]  # nada de B


def test_object_out_of_scope_or_of_another_tenant_is_404_and_unchanged(
    api: Any, migrator: psycopg.Connection[Any]
) -> None:
    give(api.a, api.membership, {VIEW: "OWN", MANAGE: "OWN"})
    hidden = (api.theirs, api.orgs["widget_A"], api.orgs["widget_B"], uuid4())
    replies = {
        send(api.client, method, detail(pk))
        for pk in hidden  # de otra persona, de nadie, de otra organización e inexistente
        for method in ("GET", "PATCH", "PUT", "DELETE")
    }
    assert len(replies) == 1 and replies.pop()[0] == 404  # indistinguibles entre sí
    assert names(migrator) == ["mine", "theirs", "widget A", "widget B"]
    assert WidgetSerializer().fields["id"].read_only  # un `id` escribible delataría a otro tenant
    assert send(api.client, "PATCH", detail(api.mine))[0] == 200  # el suyo, sí
    assert names(migrator) == ["cambiado", "theirs", "widget A", "widget B"]
    assert send(api.client, "DELETE", detail(api.mine))[0] == 204
    assert names(migrator) == ["theirs", "widget A", "widget B"]


def test_write_scope_narrower_than_read_scope_is_404_and_unchanged(
    api: Any, migrator: psycopg.Connection[Any]
) -> None:
    give(api.a, api.membership, {VIEW: "ORGANIZATION", MANAGE: "OWN"})
    assert api.client.get(detail(api.theirs)).status_code == 200  # lo ve
    for method in ("PATCH", "PUT", "DELETE"):  # pero cada método usa su permiso y su alcance
        reply = send(api.client, method, detail(api.theirs))  # lo oculta el filtro, en SQL
        assert reply[0] == 404 and reply == send(api.client, method, detail(uuid4()))
    assert names(migrator) == ["mine", "theirs", "widget A", "widget B"]
    assert send(api.client, "PATCH", detail(api.mine))[0] == 200


def test_object_check_is_a_second_barrier_and_nothing_passes_without_tenant(api: Any) -> None:
    give(api.a, api.membership, {VIEW: "OWN", MANAGE: "OWN"})
    check, get = HasPermission().has_object_permission, SimpleNamespace(method="GET")
    mine = Widget(organization_id=api.a, assigned_user_id=api.ana.pk)
    with tenant_scope(ctx(api.a, api.ana)):
        assert check(get, WidgetDetail(), mine)
        for hidden in (
            Widget(organization_id=api.a),  # de nadie
            Widget(organization_id=api.b, assigned_user_id=api.ana.pk),  # de otra organización
        ):
            for method in ("GET", "PUT", "PATCH", "DELETE"):
                with pytest.raises(NotFound):
                    check(SimpleNamespace(method=method), WidgetDetail(), hidden)
        assert not check(SimpleNamespace(method="DELETE"), Partial(), mine)  # sin declarar
        assert not HasPermission().has_permission(get, SimpleNamespace(required_permissions=VIEW))
        none = ScopeFilter().filter_queryset(get, Widget.objects.all(), Undeclared())
        assert none.query.is_empty()  # sin declaración, ninguna fila
    assert not HasPermission().has_permission(get, WidgetList())  # sin contexto de tenant
    assert not check(get, WidgetDetail(), mine)
    none = ScopeFilter().filter_queryset(get, Widget._base_manager.all(), WidgetList())
    assert none.query.is_empty()


def test_permissions_are_read_once_per_request_and_again_on_the_next(api: Any) -> None:
    role = give(api.a, api.membership, {VIEW: "OWN"})
    with CaptureQueriesContext(connection) as queries:
        assert api.client.get(detail(api.mine)).status_code == 200
    grants = [query for query in queries if "role_permissions" in query["sql"]]
    assert len(grants) == 1  # permiso, filtro y objeto comparten una sola lectura
    with CaptureQueriesContext(connection) as queries:
        assert send(api.client, "OPTIONS", detail(api.mine, "described/"))[0] == 200
    grants = [query for query in queries if "role_permissions" in query["sql"]]
    assert len(grants) == 1  # también cuando DRF clona su Request para describir la vista
    with tenant_scope(ctx(api.a)):
        RolePermission.objects.filter(role=role).delete()
    assert api.client.get(detail(api.mine)).status_code == 403  # nada queda entre peticiones


def test_custom_role_and_renamed_owner_count_only_by_their_grants(api: Any) -> None:
    give(api.a, api.membership, {VIEW: "ORGANIZATION"}, code="warehouse_manager")
    assert len(api.client.get(url()).json()) == 3  # rol propio de la organización
    assert api.client.get(url("members/")).status_code == 403
    with tenant_scope(ctx(api.a)) as scope:
        owner = next(role for role in clone_role_templates(scope) if role.is_owner_role)
        MembershipRole.objects.create(membership_id=api.membership, role=owner)
    assert api.client.get(url("members/")).status_code == 200
    with tenant_scope(ctx(api.a)):
        Role.objects.filter(pk=owner.pk).update(code="fundador", name="Otro nombre")
    assert api.client.get(url("members/")).status_code == 200  # renombrarlo no cambia nada
    with tenant_scope(ctx(api.a)):  # Owner por código, nombre y marca, pero sin la concesión
        Role.objects.filter(pk=owner.pk).update(code="owner", name="Owner")
        RolePermission.objects.filter(role=owner, permission_id="users.view").delete()
    assert api.client.get(url("members/")).status_code == 403


def test_platform_staff_gets_no_bypass_and_platform_routes_are_excluded_by_route(api: Any) -> None:
    staff = User.objects.create_superuser("ops@example.com", TEST_PASSWORD)
    client = Client()
    client.force_login(staff)
    for target in (url(), detail(api.mine), url("members/"), url("undeclared/")):
        assert send(client, "GET", target) == (404, b'{"code": "NOT_FOUND"}')  # sin membresía
    membership = join(api.a, staff)
    for target in (url(), detail(api.mine), url("members/"), url("undeclared/")):
        assert client.get(target).status_code == 403  # con membresía y sin concesiones
    give(api.a, membership.pk, {VIEW: "OWN"})
    assert client.get(url()).json() == []  # solo lo que conceden sus roles
    for anybody in (Client(), api.client, client):
        assert anybody.get("/platform/open/").status_code == 200  # la vista declara sus clases
        assert anybody.get("/platform/defaults/").status_code == 403  # sin declarar: denegada


def test_every_tenant_route_declares_its_permissions(api: Any) -> None:
    assert insecure(config.urls.urlpatterns, PLATFORM) == {}  # el proyecto real
    assert insecure(secure, frozenset({"platform/open/"})) == {}
    assert TENANT_PATH.match("/api/v1/o/org-a/") and not TENANT_PATH.match("/api/v1/x/org-a/")


def test_audit_flags_every_insecure_route(api: Any) -> None:
    found = insecure(urlpatterns, frozenset({"platform/open/"}))
    flawed = {route: reason for entry, reason in FLAWED for route, _ in routes([entry])}
    assert set(found) == set(flawed) and len(flawed) == len(FLAWED)
    for route, reason in flawed.items():
        assert reason in found[route], route
    legacy = insecure(legacy_urls.urlpatterns, PLATFORM)  # vistas de Django tras un `include()`
    assert len(legacy) == 2 and set(legacy.values()) == {"no es una vista de DRF"}
    stale = insecure(config.urls.urlpatterns, PLATFORM | {"ya/no/existe/"})
    assert stale == {"ya/no/existe/": "exclusión de plataforma obsoleta"}
