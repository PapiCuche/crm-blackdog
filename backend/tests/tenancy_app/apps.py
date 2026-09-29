from django.apps import AppConfig


class TenancyTestAppConfig(AppConfig):
    """App SOLO de tests (config.settings.test): valida RLS sin crear tablas de negocio."""

    name = "tests.tenancy_app"
    label = "tenancy_app"
