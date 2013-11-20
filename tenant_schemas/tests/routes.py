from django.conf import settings
from django.db import connection
from django.test import TransactionTestCase
from django.test.client import RequestFactory
from tenant_schemas.middleware import TenantMiddleware
from tenant_schemas.tests.models import Tenant
from tenant_schemas.utils import get_public_schema_name


class RoutesTestCase(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        settings.TENANT_APPS = ('tenant_schemas',
                                'django.contrib.contenttypes',
                                'django.contrib.auth', )

    def setUp(self):
        self.factory = RequestFactory()
        self.tm = TenantMiddleware()

        # settings needs some patching
        settings.TENANT_MODEL = 'tenant_schemas.Tenant'

        # add the public tenant
        self.public_tenant_domain = 'test.com'
        self.public_tenant = Tenant(domain_url=self.public_tenant_domain,
                                    schema_name='public')
        self.public_tenant.save()

        # add a test tenant
        self.tenant_domain = 'tenant.test.com'
        self.tenant = Tenant(domain_url=self.tenant_domain, schema_name='test')
        self.tenant.save()

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

    def test_tenant_routing(self):
        """
        request path should not be altered
        """
        request_url = '/any/request/'
        request = self.factory.get('/any/request/',
                                   HTTP_HOST=self.tenant_domain)
        self.tm.process_request(request)

        self.assertEquals(request.path_info, request_url)

        # request.tenant should also have been set
        self.assertEquals(request.tenant, self.tenant)

    def test_public_schema_routing(self):
        """
        request path should not be altered
        """
        request_url = '/any/request/'
        request = self.factory.get('/any/request/',
                                   HTTP_HOST=self.public_tenant_domain)
        self.tm.process_request(request)

        self.assertEquals(request.path_info, request_url)

        # request.tenant should also have been set
        self.assertEquals(request.tenant, self.public_tenant)
