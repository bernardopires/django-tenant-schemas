from contextlib import contextmanager
from django.conf import settings
from django.db import connection
from django.db.models.loading import get_model
from django.core import mail
from django.core.exceptions import ImproperlyConfigured

@contextmanager
def schema_context(schema_name):
    previous_tenant = connection.tenant
    try:
        connection.set_schema(schema_name)
        yield
    finally:
        if previous_tenant is None:
            connection.set_schema_to_public()
        else:
            connection.set_tenant(previous_tenant)


@contextmanager
def tenant_context(tenant):
    previous_tenant = connection.tenant
    try:
        connection.set_tenant(tenant)
        yield
    finally:
        if previous_tenant is None:
            connection.set_schema_to_public()
        else:
            connection.set_tenant(previous_tenant)


def get_tenant_model():
    return get_model(*settings.TENANT_MODEL.split("."))

def get_tenant_adapter():
    adapter = getattr(settings, 'TENANT_ADAPTER',
            'tenant_schemas.adapters.ModelTenantAdapter')
    try:
        module, name = adapter.rsplit('.', 1)
    except ValueError:
        raise ImproperlyConfigured('TENANT_ADAPTER must contain at least a dot: '
                '%r' % adapter)
    try:
        module = __import__(module)
    except ImportError, e:
        raise ImproperlyConfigured('module "%s" in TENANT_ADAPTER does not '
                'exist: %s' % (module, e))
    try:
        return getattr(module, name)
    except AttributeError, e:
        raise ImproperlyConfigured('module "%s" does not define a "%s" '
                'TENANT_ADAPTER class: %s' % (module, name, e))

def get_public_schema_name():
    return getattr(settings, 'PUBLIC_SCHEMA_NAME', 'public')


def clean_tenant_url(url_string):
    """
    Removes the TENANT_TOKEN from a particular string
    """
    if hasattr(settings, 'PUBLIC_SCHEMA_URLCONF'):
        if (settings.PUBLIC_SCHEMA_URLCONF
                and url_string.startswith(settings.PUBLIC_SCHEMA_URLCONF)):
            url_string = url_string[len(settings.PUBLIC_SCHEMA_URLCONF):]
    return url_string


def remove_www_and_dev(hostname):
    """
    Removes www. and dev. from the beginning of the address. Only for
    routing purposes. www.test.com/login/ and test.com/login/ should
    find the same tenant.
    """
    if hostname.startswith("www.") or hostname.startswith("dev."):
        return hostname[4:]

    return hostname


def django_is_in_test_mode():
    """
    I know this is very ugly! I'm looking for more elegant solutions.
    See: http://stackoverflow.com/questions/6957016/detect-django-testing-mode
    """
    return hasattr(mail, 'outbox')


def schema_exists(schema_name):
    cursor = connection.cursor()

    # check if this schema already exists in the db
    sql = 'SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_namespace WHERE nspname = %s)'
    cursor.execute(sql, (schema_name, ))

    row = cursor.fetchone()
    if row:
        exists = row[0]
    else:
        exists = False

    cursor.close()

    return exists
