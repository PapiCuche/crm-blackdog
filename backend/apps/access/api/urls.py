from django.urls import path

from apps.access.api import views

urlpatterns = [
    path("me/", views.SelfContextView.as_view(), name="me-context"),
]
