import warnings

import django
from django.conf import settings
from django.core.checks import register
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.db.utils import ProgrammingError

from django.core.checks import Critical, Warning


from tenant_schemas.utils import get_public_schema_name, get_tenant_model


IS_DJANGO17 = django.VERSION >= (1, 7, 0)


@register()
def tenant_schemas_check(app_configs, **kwargs):
    errors = []
    # ... your check logic here

    # Make a bunch of tests for configuration recommendations
    # These are best practices basically, to avoid hard to find bugs,
    # unexpected behaviour
    if not hasattr(settings, 'TENANT_APPS'):
        errors.append(_make_error(
            'TENANT_APPS setting not set',
            id='tenant_schemas.E001',
            error_class=Critical,
            exception_class=ImproperlyConfigured
        ))

    if not getattr(settings, 'TENANT_APPS', []):
        errors.append(_make_error(
            'TENANT_APPS is empty',
            hint="Maybe you didn't need this app?",
            id='tenant_schemas.E002',
            error_class=Critical,
            exception_class=ImproperlyConfigured))

    if IS_DJANGO17:
        ideal_app_position = 0
    else:
        ideal_app_position = -1

    if settings.INSTALLED_APPS[ideal_app_position] != 'tenant_schemas':
        print _get_recommended_config()

    if hasattr(settings, 'PG_EXTRA_SEARCH_PATHS'):
        if get_public_schema_name() in settings.PG_EXTRA_SEARCH_PATHS:
            errors.append(_make_error(
                "%s can not be included on PG_EXTRA_SEARCH_PATHS." %
                get_public_schema_name(),
                id='tenant_schemas.E003',
                error_class=Critical,
                exception_class=ImproperlyConfigured))

        # Do not run the following if public is not on search_paths. This is
        # valid for situations like migrate_schemas --tenant
        if not connection.include_public_schema:
            return errors

        # make sure no tenant schema is in settings.PG_EXTRA_SEARCH_PATHS
        # and if tenants table has not been synched yet then provide a
        # helpful warning
        TenantModel = get_tenant_model()
        try:
            schemas = list(TenantModel.objects.all().values_list(
                'schema_name', flat=True))
        except ProgrammingError, e:
            table = TenantModel._meta.db_table
            if 'relation "{}" does not exist'.format(table) not in e:
                errors.append(_make_error(
                    "Missing Tenants Table",
                    hint=_get_missing_tenants_table_message(),
                    id='tenant_schemas.E004',
                    error_class=Warning
                ))

            schemas = []
        invalid_schemas = set(settings.PG_EXTRA_SEARCH_PATHS).intersection(
            schemas)
        if invalid_schemas:
            errors.append(_make_error(
                "Bad PG_EXTRA_SEARCH_PATHS",
                hint="Do not include tenant schemas (%s) on "
                "PG_EXTRA_SEARCH_PATHS." % list(invalid_schemas),
                id='tenant_schemas.E005',
                error_class=Critical,
                exception_class=ImproperlyConfigured
            ))
    return errors


def _make_error(message, error_class, exception_class=None, hint=None,
                obj=None, id=None):
    if IS_DJANGO17:
        return error_class(message, hint, obj, id)
    else:
        if exception_class:
            raise exception_class(message)
        else:
            warnings.warn('\n\n'.join([message, hint]))


def _get_missing_tenants_table_message():
    if IS_DJANGO17:
        return ("""
=======================================================================
Looks like the tenants table has not been synched to the DB yet.
Run `python manage.py migrate_schemas --shared` to do so.
=======================================================================""")
    else:
        return ("""
=======================================================================
Looks like the tenants table has not been synched to the DB yet.
Run `python manage.py sync_schemas --shared` and `python manage.py migrate_schemas --shared` to do so.
=======================================================================""")


def _get_recommended_config():
    if IS_DJANGO17:
        return """
Warning: You should put 'tenant_schemas' at the start of
INSTALLED_APPS like this: INSTALLED_APPS = ('tenant_schemas',) + TENANT_APPS + SHARED_APPS.
This is necessary to overwrite built-in django management commands with their schema-aware implementations.
"""
    else:
        return """
Warning: You should put 'tenant_schemas' at the end of
INSTALLED_APPS like this: INSTALLED_APPS = TENANT_APPS + SHARED_APPS +
('tenant_schemas',) This is necessary to overwrite built-in django
management commands with their schema-aware implementations.
"""
