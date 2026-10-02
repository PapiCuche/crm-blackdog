from django.urls import path

from apps.accounts.api import views

urlpatterns = [
    path("csrf/", views.CsrfView.as_view(), name="auth-csrf"),
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("session/", views.SessionView.as_view(), name="auth-session"),
]
