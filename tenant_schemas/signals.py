from django.core.exceptions import ImproperlyConfigured
from django.dispatch import Signal
from django.conf import settings
from tenant_schemas.utils import get_public_schema_name, get_tenant_model

post_schema_sync = Signal(providing_args=['tenant'])
post_schema_sync.__doc__ = """
Sent after a tenant has been saved, its schema created and synced
"""

def validate_schemas_on_pg_extras_paths():
    if hasattr(settings, 'PG_EXTRA_SEARCH_PATHS'):
        if get_public_schema_name() in settings.PG_EXTRA_SEARCH_PATHS:
            raise ImproperlyConfigured(
                "%s can not be included on PG_EXTRA_SEARCH_PATHS."
                % get_public_schema_name())

        # make sure no tenant schema is in settings.PG_EXTRA_SEARCH_PATHS
        invalid_schemas = set(settings.PG_EXTRA_SEARCH_PATHS).intersection(
            get_tenant_model().objects.all().values_list('schema_name', flat=True))
        if invalid_schemas:
            raise ImproperlyConfigured(
                "Do not include tenant schemas (%s) on PG_EXTRA_SEARCH_PATHS."
                % list(invalid_schemas))