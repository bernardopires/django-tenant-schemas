import warnings
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from tenant_schemas.utils import get_public_schema_name, get_tenant_model


recommended_config = """
Warning: You should put 'tenant_schemas' at the end of INSTALLED_APPS like this:
INSTALLED_APPS = TENANT_APPS + SHARED_APPS + ('tenant_schemas',)
This is necessary to overwrite built-in django management commands with their schema-aware implementations.
"""
# Make a bunch of tests for configuration recommendations
# These are best practices basically, to avoid hard to find bugs, unexpected behaviour
if not hasattr(settings, 'TENANT_APPS'):
    raise ImproperlyConfigured('TENANT_APPS setting not set')

if not settings.TENANT_APPS:
    raise ImproperlyConfigured("TENANT_APPS is empty. Maybe you don't need this app?")

if settings.INSTALLED_APPS[-1] != 'tenant_schemas':
    warnings.warn(recommended_config, SyntaxWarning)

if hasattr(settings, 'PG_EXTRA_SEARCH_PATHS'):
    if get_public_schema_name() in settings.PG_EXTRA_SEARCH_PATHS:
        raise ImproperlyConfigured("%s can not be included on PG_EXTRA_SEARCH_PATHS." % get_public_schema_name())

    # make sure no tenant schema is in settings.PG_EXTRA_SEARCH_PATHS
    invalid_schemas = set(settings.PG_EXTRA_SEARCH_PATHS).intersection(
        get_tenant_model().objects.all().values_list('schema_name', flat=True))
    if invalid_schemas:
        raise ImproperlyConfigured("Do not include tenant schemas (%s) on PG_EXTRA_SEARCH_PATHS."
                                   % list(invalid_schemas))

