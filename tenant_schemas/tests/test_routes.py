from django.conf import settings
from django.test.client import RequestFactory

from tenant_schemas.middleware import TenantMiddleware
from tenant_schemas.tests.testcases import BaseTestCase
from tenant_schemas.utils import get_public_schema_name, get_tenant_model


class RoutesTestCase(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super(RoutesTestCase, cls).setUpClass()
        settings.SHARED_APPS = ('tenant_schemas',
                                'customers')
        settings.TENANT_APPS = ('dts_test_app',
                                'django.contrib.contenttypes',
                                'django.contrib.auth',)
        settings.INSTALLED_APPS = settings.SHARED_APPS + settings.TENANT_APPS
        cls.available_apps = settings.INSTALLED_APPS
        cls.sync_shared()

        cls.public_tenant = get_tenant_model()(domain_url='test.com', schema_name=get_public_schema_name())
        cls.public_tenant.save(verbosity=BaseTestCase.get_verbosity())

    @classmethod
    def tearDownClass(cls):
        from django.db import connection

        connection.set_schema_to_public()

        cls.public_tenant.delete()

        super(RoutesTestCase, cls).tearDownClass()

    def setUp(self):
        super(RoutesTestCase, self).setUp()
        self.factory = RequestFactory()
        self.tm = TenantMiddleware()

        self.tenant_domain = 'tenant.test.com'
        self.tenant = get_tenant_model()(domain_url=self.tenant_domain, schema_name='test')
        self.tenant.save(verbosity=BaseTestCase.get_verbosity())

    def tearDown(self):
        from django.db import connection

        connection.set_schema_to_public()

        self.tenant.delete(force_drop=True)

        super(RoutesTestCase, self).tearDown()

    def test_tenant_routing(self):
        """
        Request path should not be altered.
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
        Request path should not be altered.
        """
        request_url = '/any/request/'
        request = self.factory.get('/any/request/',
                                   HTTP_HOST=self.public_tenant.domain_url)
        self.tm.process_request(request)

        self.assertEquals(request.path_info, request_url)

        # request.tenant should also have been set
        self.assertEquals(request.tenant, self.public_tenant)
