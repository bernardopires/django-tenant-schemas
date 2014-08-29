import django
from django.apps import AppConfig


class TenantSchemasConfig(AppConfig):
    name = 'tenant_schemas'
    verbose_name = 'Tenant Schemas'

    def ready(self):
        from . import checks
        if django.VERSION < (1, 7, 0):
            checks.tenant_schemas_check([])
