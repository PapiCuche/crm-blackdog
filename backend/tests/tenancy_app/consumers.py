from typing import Any

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from core.tenancy.channels import TenantConsumerMixin
from tests.tenancy_app.models import Widget


class WidgetConsumer(TenantConsumerMixin, AsyncJsonWebsocketConsumer):  # type: ignore[misc]
    async def connect(self) -> None:
        if await self.connect_tenant():
            await self.accept()

    async def receive_json(self, content: Any, **kwargs: Any) -> None:
        pk = content["subscribe"]
        visible = await self.in_tenant(lambda: Widget.objects.filter(pk=pk).exists())
        await self.send_json({"subscribed": pk} if visible else {"error": "NOT_FOUND"})
