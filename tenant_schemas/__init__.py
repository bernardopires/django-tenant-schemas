import django

if django.VERSION >= (1, 7, 0):
    default_app_config = 'tenant_schemas.apps.TenantSchemasConfig'
else:
    from .apps import TenantSchemasConfig
    TenantSchemasConfig().ready()
