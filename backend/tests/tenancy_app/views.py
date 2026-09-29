from uuid import UUID

from django.http import HttpRequest, JsonResponse

from core.tenancy.middleware import not_found
from tests.tenancy_app.models import Widget


def widget_list(request: HttpRequest, org_slug: str) -> JsonResponse:
    return JsonResponse({"ids": [str(i) for i in Widget.objects.values_list("id", flat=True)]})


def widget_detail(request: HttpRequest, org_slug: str, pk: UUID) -> JsonResponse:
    widget = Widget.objects.filter(pk=pk).first()
    if widget is None:
        return not_found()
    if request.method == "PATCH":
        widget.name = "cambiado"
        widget.save()
    elif request.method == "DELETE":
        widget.delete()
    return JsonResponse({"id": str(pk)})
