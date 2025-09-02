import inspect

from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings

from tenant_schemas.utils import get_public_schema_name


@override_settings(
    TENANT_MODEL="tenant_schemas.Tenant",
    SHARED_APPS=("tenant_schemas",),
    TENANT_APPS=("dts_test_app", "django.contrib.contenttypes", "django.contrib.auth"),
    INSTALLED_APPS=(
        "tenant_schemas",
        "dts_test_app",
        "django.contrib.contenttypes",
        "django.contrib.auth",
    ),
)
class BaseTestCase(TestCase):
    """
    Base test case that comes packed with overloaded INSTALLED_APPS,
    custom public tenant, and schemas cleanup on tearDown.
    """

    @classmethod
    def setUpClass(cls):
        # Add .test.com to ALLOWED_HOSTS for testing
        cls.original_allowed_hosts = list(settings.ALLOWED_HOSTS)
        if ".test.com" not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS = cls.original_allowed_hosts + [".test.com"]

        # Django calls syncdb by default for the test database, but we want
        # a blank public schema for this set of tests.
        connection.set_schema_to_public()
        cursor = connection.cursor()
        cursor.execute(
            "DROP SCHEMA IF EXISTS %s CASCADE; CREATE SCHEMA %s;"
            % (get_public_schema_name(), get_public_schema_name())
        )
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        # Restore original ALLOWED_HOSTS
        if hasattr(cls, "original_allowed_hosts"):
            settings.ALLOWED_HOSTS = cls.original_allowed_hosts
        super().tearDownClass()

    def setUp(self):
        connection.set_schema_to_public()
        super().setUp()

    @classmethod
    def get_verbosity(self):
        for s in reversed(inspect.stack()):
            options = s[0].f_locals.get("options")
            if isinstance(options, dict):
                return int(options["verbosity"]) - 2
        return 1

    @classmethod
    def get_tables_list_in_schema(cls, schema_name):
        cursor = connection.cursor()
        sql = """SELECT table_name FROM information_schema.tables
              WHERE table_schema = %s"""
        cursor.execute(sql, (schema_name,))
        return [row[0] for row in cursor.fetchall()]

    @classmethod
    def sync_shared(cls):
        call_command(
            "migrate_schemas",
            schema_name=get_public_schema_name(),
            interactive=False,
            verbosity=cls.get_verbosity(),
            run_syncdb=True,
        )
