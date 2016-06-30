from django.apps import AppConfig


class TenantSchemasConfig(AppConfig):

    name = 'tenant_schemas'
    verbose_name = 'Tenant Schemas'

    def ready(self):
        from signals import validate_schemas_on_pg_extras_paths
        validate_schemas_on_pg_extras_paths()