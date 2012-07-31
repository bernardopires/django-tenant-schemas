from contextlib import contextmanager
from django.conf import settings
from django.db import connection
from django.db.models.loading import get_model
from django.core import mail

@contextmanager
def schema_context(schema_name):
    previous_schema = connection.get_schema()
    try:
        connection.set_schema(schema_name)
        yield
    finally:
        connection.set_schema(previous_schema)

@contextmanager
def tenant_context(tenant):
    previous_schema = connection.get_schema()
    try:
        connection.set_tenant(tenant)
        yield
    finally:
        connection.set_schema(previous_schema)

def get_tenant_model():
    return get_model(*settings.TENANT_MODEL.split("."))

def clean_tenant_url(url_string):
    """
    Removes the TENANT_TOKEN from a particular string
    """
    if url_string.startswith(settings.TENANT_URL_TOKEN):
        url_string = url_string[5:]
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
    sql = 'SELECT schema_name FROM information_schema.schemata '\
          'WHERE schema_name = %s'
    cursor.execute(sql, (schema_name, ))

    exists = len(cursor.fetchall()) > 0

    cursor.close()

    return exists
