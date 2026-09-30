from django.urls import path
from drf_spectacular.views import SpectacularAPIView

from core import health

urlpatterns = [
    path("health/live", health.live, name="health-live"),
    path("health/ready", health.ready, name="health-ready"),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),  # contrato OpenAPI
]
