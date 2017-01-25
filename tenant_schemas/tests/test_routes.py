from django.conf import settings
from django.test.client import RequestFactory

from tenant_schemas.middleware import (
    TenantMiddleware, DefaultSchemaTenantMiddleware)
from tenant_schemas.tests.models import Tenant
from tenant_schemas.tests.testcases import BaseTestCase
from tenant_schemas.utils import get_public_schema_name


class RoutesTestCase(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super(RoutesTestCase, cls).setUpClass()
        settings.SHARED_APPS = ('tenant_schemas', )
        settings.TENANT_APPS = ('dts_test_app',
                                'django.contrib.contenttypes',
                                'django.contrib.auth', )
        settings.INSTALLED_APPS = settings.SHARED_APPS + settings.TENANT_APPS
        cls.sync_shared()
        cls.public_tenant = Tenant(domain_url='test.com', schema_name=get_public_schema_name())
        cls.public_tenant.save(verbosity=BaseTestCase.get_verbosity())

    def setUp(self):
        super(RoutesTestCase, self).setUp()
        self.factory = RequestFactory()
        self.tm = TenantMiddleware()

        self.tenant_domain = 'tenant.test.com'
        self.tenant = Tenant(domain_url=self.tenant_domain, schema_name='test')
        self.tenant.save(verbosity=BaseTestCase.get_verbosity())

        self.non_exisitant_domain = 'no-tenant.test.com'
        self.non_exisitant_tenant = Tenant(domain_url=self.non_exisitant_domain, schema_name='no-tenant')

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

    def test_non_exisitant_tenant_routing(self):
        """
        Request path should not be altered.
        """
        request = self.factory.get('/any/request/',
                                   HTTP_HOST=self.non_exisitant_tenant.domain_url)

        self.assertRaises(self.tm.TENANT_NOT_FOUND_EXCEPTION, self.tm.process_request, request)

    def test_existent_tenant_to_schema_routing(self):
        """
        Request path should not be altered.
        """
        with self.settings(DEFAULT_SCHEMA_NAME=self.non_exisitant_tenant.schema_name):
            self.tm = DefaultSchemaTenantMiddleware()

            request_url = '/any/request/'
            request = self.factory.get('/any/request/',
                                       HTTP_HOST=self.tenant_domain)
            self.tm.process_request(request)

            self.assertEquals(request.path_info, request_url)

            # request.tenant should also have been set
            self.assertEquals(request.tenant, self.tenant)

    def test_non_existent_tenant_to_default_schema_routing(self):
        """
        Request path should not be altered.
        """
        with self.settings(DEFAULT_SCHEMA_NAME=self.tenant.schema_name):
            self.tm = DefaultSchemaTenantMiddleware()

            request_url = '/any/request/'
            request = self.factory.get('/any/request/',
                                       HTTP_HOST=self.non_exisitant_domain)
            self.tm.process_request(request)

            self.assertEquals(request.path_info, request_url)

            # request.tenant should also have been set
            self.assertEquals(request.tenant, self.tenant)

    def test_non_existent_tenant_to_non_existing_default_schema_routing(self):
        """
        Request path should not be altered.
        """
        with self.settings(DEFAULT_SCHEMA_NAME=self.non_exisitant_tenant.schema_name):
            self.tm = DefaultSchemaTenantMiddleware()

            request = self.factory.get('/any/request/',
                                       HTTP_HOST=self.non_exisitant_domain)

            self.assertRaises(self.tm.TENANT_NOT_FOUND_EXCEPTION,
                              self.tm.process_request, request)

    def test_non_existent_tenant_default_schema_not_set_routing(self):
        """
        Request path should not be altered.
        """
        self.tm = DefaultSchemaTenantMiddleware()

        request = self.factory.get('/any/request/',
                                   HTTP_HOST=self.non_exisitant_domain)

        self.assertRaises(self.tm.TENANT_NOT_FOUND_EXCEPTION,
                          self.tm.process_request, request)
