from django.apps import AppConfig
from django.core import checks
from django.core.files.storage import default_storage
from tenant_schemas.storage import TenantStorageMixin


class TenantSchemasConfig(AppConfig):
    name = 'tenant_schemas'


@checks.register('storage')
def tenant_storage(app_configs, **kwargs):
    """
    Check if the project is taking advantage of our tenant aware storage.
    """
    errors = []
    
    if not isinstance(default_storage, TenantStorageMixin):
        errors.append(checks.Warning(
            "Your default storage engine is not tenant aware.",
            hint="Set settings.DEFAULT_FILE_STORAGE to "
                 "'tenant_schemas.storage.TenantFileSystemStorage'",
        ))

    return errors
