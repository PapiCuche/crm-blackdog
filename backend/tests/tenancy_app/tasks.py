from core.tenancy.celery import platform_task, tenant_task
from tests.tenancy_app.models import Widget


@tenant_task(name="tenancy_app.visible_widgets")
def visible_widgets() -> list[str]:
    return [str(i) for i in Widget.objects.values_list("id", flat=True)]


PINGS: list[str] = []  # ejecuciones reales del cuerpo de platform_ping


@platform_task(name="tenancy_app.platform_ping")
def platform_ping() -> str:
    PINGS.append("ok")
    return "ok"


@platform_task(name="tenancy_app.count_without_tenant")
def count_without_tenant() -> int:
    return Widget.objects.count()  # sin tenant: TenantContextMissing
