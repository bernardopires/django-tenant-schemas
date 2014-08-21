from django.conf import settings
from django.db import connection
from django.test import TransactionTestCase

from .models import Tenant
from ..utils import get_public_schema_name


class BaseTestCase(TransactionTestCase):
    """ Base test case that comes packed with overloaded INSTALLED_APPS,
        custom public tenant, and schemas cleanup on tearDown.
    """
    @classmethod
    def setUpClass(cls):
        settings.TENANT_APPS = ('tenant_schemas',
                                'django.contrib.contenttypes',
                                'django.contrib.auth', )

    def setUp(self):
        # settings needs some patching
        settings.TENANT_MODEL = 'tenant_schemas.Tenant'

        # add the public tenant
        self.public_tenant_domain = 'test.com'
        self.public_tenant = Tenant(domain_url=self.public_tenant_domain,
                                    schema_name='public')
        self.public_tenant.save()

        connection.set_schema_to_public()

    def tearDown(self):
        """
        Delete all tenant schemas. Tenant schema are not deleted
        automatically by django.
        """
        connection.set_schema_to_public()
        do_not_delete = [get_public_schema_name(), 'information_schema']
        cursor = connection.cursor()

        # Use information_schema.schemata instead of pg_catalog.pg_namespace in
        # utils.schema_exists, so that we only "see" schemas that we own
        cursor.execute('SELECT schema_name FROM information_schema.schemata')

        for row in cursor.fetchall():
            if not row[0].startswith('pg_') and row[0] not in do_not_delete:
                print("Deleting schema %s" % row[0])
                cursor.execute('DROP SCHEMA %s CASCADE' % row[0])

        Tenant.objects.all().delete()
