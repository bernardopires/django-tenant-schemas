from contextlib import contextmanager

from django.conf import settings
from django.db import connection

try:
    from django.apps import apps, AppConfig

    get_model = apps.get_model
except ImportError:
    from django.db.models.loading import get_model

    AppConfig = None
from django.core import mail

MULTI_DB_ENABLED = True if len(settings.DATABASES.keys()) > 1 else False


def get_db_alias():
    return settings.DATABASES.keys()


# Changes to schema_context and tenant_context when multi db enabled
if MULTI_DB_ENABLED:
    from django.db import connections


    def get_previous_tenant_dict():
        previous_tenant_dict = dict()
        for db in get_db_alias():
            previous_tenant_dict[db] = connections[db].tenant
        return previous_tenant_dict


    def apply_previous_tenant_dict(previous_tenant_dict):
        if not previous_tenant_dict:
            for db in get_db_alias():
                connections[db].set_schema_to_public()
        else:
            for db in get_db_alias():
                connections[db].set_tenant(previous_tenant_dict[db])


    @contextmanager
    def schema_context(schema_name):
        previous_tenant_dict = get_previous_tenant_dict()
        try:
            for db in get_db_alias():
                connections[db].set_schema(schema_name)
            yield
        finally:
            apply_previous_tenant_dict(previous_tenant_dict)


    @contextmanager
    def tenant_context(tenant):
        previous_tenant_dict = get_previous_tenant_dict()
        try:
            for db in get_db_alias():
                connections[db].set_tenant(tenant)
            yield
        finally:
            apply_previous_tenant_dict(previous_tenant_dict)
else:
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


def get_public_schema_name():
    return getattr(settings, 'PUBLIC_SCHEMA_NAME', 'public')


def get_limit_set_calls():
    return getattr(settings, 'TENANT_LIMIT_SET_CALLS', False)


def clean_tenant_url(url_string):
    """
    Removes the TENANT_TOKEN from a particular string
    """
    if hasattr(settings, 'PUBLIC_SCHEMA_URLCONF'):
        if (settings.PUBLIC_SCHEMA_URLCONF and
                url_string.startswith(settings.PUBLIC_SCHEMA_URLCONF)):
            url_string = url_string[len(settings.PUBLIC_SCHEMA_URLCONF):]
    return url_string


def remove_www_and_dev(hostname):
    """
    Legacy function - just in case someone is still using the old name
    """
    return remove_www(hostname)


def remove_www(hostname):
    """
    Removes www. from the beginning of the address. Only for
    routing purposes. www.test.com/login/ and test.com/login/ should
    find the same tenant.
    """
    if hostname.startswith("www."):
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
    sql = 'SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_namespace WHERE LOWER(nspname) = LOWER(%s))'
    cursor.execute(sql, (schema_name, ))

    row = cursor.fetchone()
    if row:
        exists = row[0]
    else:
        exists = False

    cursor.close()

    return exists


def app_labels(apps_list):
    """
    Returns a list of app labels of the given apps_list, now properly handles
     new Django 1.7+ application registry.

    https://docs.djangoproject.com/en/1.8/ref/applications/#django.apps.AppConfig.label
    """
    if AppConfig is None:
        return [app.split('.')[-1] for app in apps_list]
    return [AppConfig.create(app).label for app in apps_list]
