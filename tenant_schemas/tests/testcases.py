import inspect

from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.test import TransactionTestCase

from tenant_schemas.utils import get_public_schema_name


class BaseTestCase(TransactionTestCase):
    """
    Base test case that comes packed with overloaded INSTALLED_APPS,
    custom public tenant, and schemas cleanup on tearDown.
    """
    @classmethod
    def setUpClass(cls):
        settings.TENANT_MODEL = 'customers.Client'
        settings.SHARED_APPS = ('tenant_schemas', 'customers')
        settings.TENANT_APPS = ('dts_test_app',
                                'django.contrib.contenttypes',
                                'django.contrib.auth', )
        settings.INSTALLED_APPS = settings.SHARED_APPS + settings.TENANT_APPS

        cls.available_apps = settings.INSTALLED_APPS

        super(BaseTestCase, cls).setUpClass()

    def setUp(self):
        connection.set_schema_to_public()
        super(BaseTestCase, self).setUp()

    @classmethod
    def get_verbosity(cls):
        for s in reversed(inspect.stack()):
            options = s[0].f_locals.get('options')
            if isinstance(options, dict):
                return int(options['verbosity']) - 2
        return 1

    @classmethod
    def get_tables_list_in_schema(cls, schema_name):
        cursor = connection.cursor()
        sql = """SELECT table_name FROM information_schema.tables
              WHERE table_schema = %s"""
        cursor.execute(sql, (schema_name, ))
        return [row[0] for row in cursor.fetchall()]

    @classmethod
    def sync_shared(cls):
        call_command('migrate_schemas',
                     schema_name=get_public_schema_name(),
                     interactive=False,
                     verbosity=cls.get_verbosity())
