from django.urls import path

from apps.organizations.api import views

urlpatterns = [
    path("organizations/", views.MyOrganizationsView.as_view(), name="me-organizations"),
]
