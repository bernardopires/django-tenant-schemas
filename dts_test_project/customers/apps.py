from django.apps import AppConfig


class CustomersConfig(AppConfig):
    name = "customers"
    verbose_name = "Customers"
    default_auto_field = "django.db.models.BigAutoField"
