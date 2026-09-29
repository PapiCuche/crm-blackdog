from django.urls import include, path

from config.urls import urlpatterns as project_urlpatterns
from tests.tenancy_app import views

tenant_urlpatterns = [
    path("widgets/", views.widget_list),
    path("widgets/<uuid:pk>/", views.widget_detail),
]
urlpatterns = [
    *project_urlpatterns,
    path("api/v1/o/<slug:org_slug>/", include(tenant_urlpatterns)),
]
