from django.apps import AppConfig


class DummyAppConfig(AppConfig):
    name = "dts_test_app"
    verbose_name = "DTS Test App"
    default_auto_field = "django.db.models.BigAutoField"
