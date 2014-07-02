from django.test.client import RequestFactory

from tenant_schemas.middleware import TenantMiddleware
from tenant_schemas.tests.models import Tenant
from tenant_schemas.tests.testcases import BaseTestCase


class RoutesTestCase(BaseTestCase):
    def setUp(self):
        super(RoutesTestCase, self).setUp()
        self.factory = RequestFactory()
        self.tm = TenantMiddleware()

        self.tenant_domain = 'tenant.test.com'
        self.tenant = Tenant(domain_url=self.tenant_domain, schema_name='test')
        self.tenant.save()

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
