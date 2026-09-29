import uuid

from django.db import models

from core.db.models import TenantModel


class Widget(TenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=50)


class WidgetPart(TenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    widget = models.ForeignKey(Widget, on_delete=models.CASCADE)
