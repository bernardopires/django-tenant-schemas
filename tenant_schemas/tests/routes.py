from django.conf import settings
from django.test import TransactionTestCase
from django.test.client import RequestFactory
from tenant_schemas.middleware import TenantMiddleware
from tenant_schemas.tests.models import Tenant


class RoutesTestCase(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        settings.TENANT_APPS = ('tenant_schemas', 'django.contrib.contenttypes', 'django.contrib.auth', )

    def setUp(self):
        self.factory = RequestFactory()
        self.tm = TenantMiddleware()

        # settings needs some patching
        settings.TENANT_MODEL = 'tenant_schemas.Tenant'
        settings.PUBLIC_SCHEMA_URL_TOKEN = '/public'

        # add the public tenant
        self.public_tenant_domain = 'test.com'
        self.public_tenant = Tenant(domain_url=self.public_tenant_domain, schema_name='public')
        self.public_tenant.save()

        # add a test tenant
        self.tenant_domain = 'tenant.test.com'
        self.tenant = Tenant(domain_url=self.tenant_domain, schema_name='test')
        self.tenant.save()

    def tearDown(self):
        Tenant.objects.all().delete()

    def test_tenant_routing(self):
        """
        request path should not be altered
        """
        request_url = '/any/request/'
        request = self.factory.get('/any/request/', HTTP_HOST=self.tenant_domain)
        self.tm.process_request(request)

        self.assertEquals(request.path_info, request_url)

        # request.tenant should also have been set
        self.assertEquals(request.tenant, self.tenant)

    def test_public_schema_routing(self):
        """
        request path should get prepended with PUBLIC_SCHEMA_URL_TOKEN
        """
        request_url = '/any/request/'
        request = self.factory.get('/any/request/', HTTP_HOST=self.public_tenant_domain)
        self.tm.process_request(request)

        self.assertEquals(request.path_info, settings.PUBLIC_SCHEMA_URL_TOKEN + request_url)

        # request.tenant should also have been set
        self.assertEquals(request.tenant, self.public_tenant)