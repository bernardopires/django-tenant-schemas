from django.core.exceptions import DisallowedHost
from django.http import Http404
from django.test.client import RequestFactory
from tenant_schemas.middleware import DefaultTenantMiddleware, TenantMiddleware
from tenant_schemas.tests.models import Tenant
from tenant_schemas.tests.testcases import BaseTestCase
from tenant_schemas.utils import get_public_schema_name


class TestDefaultTenantMiddleware(DefaultTenantMiddleware):
    DEFAULT_SCHEMA_NAME = "test"


class MissingDefaultTenantMiddleware(DefaultTenantMiddleware):
    DEFAULT_SCHEMA_NAME = "missing"


class RoutesTestCase(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sync_shared()
        cls.public_tenant = Tenant(
            domain_url="test.com", schema_name=get_public_schema_name()
        )
        cls.public_tenant.save(verbosity=BaseTestCase.get_verbosity())

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.tm = TenantMiddleware(lambda r: r)
        self.dtm = DefaultTenantMiddleware(lambda r: r)

        self.tenant_domain = "tenant.test.com"
        self.tenant = Tenant(domain_url=self.tenant_domain, schema_name="test")
        self.tenant.save(verbosity=BaseTestCase.get_verbosity())

        self.non_existent_domain = "no-tenant.test.com"
        self.non_existent_tenant = Tenant(
            domain_url=self.non_existent_domain, schema_name="no-tenant"
        )

        self.url = "/any/path/"

    def test_tenant_routing(self):
        request = self.factory.get(self.url, HTTP_HOST=self.tenant_domain)
        self.tm(request)
        self.assertEqual(request.path_info, self.url)
        self.assertEqual(request.tenant, self.tenant)

    def test_public_schema_routing(self):
        request = self.factory.get(self.url, HTTP_HOST=self.public_tenant.domain_url)
        self.tm(request)
        self.assertEqual(request.path_info, self.url)
        self.assertEqual(request.tenant, self.public_tenant)

    def test_non_existent_tenant_routing(self):
        """Raise 404 for unrecognised hostnames."""
        request = self.factory.get(
            self.url, HTTP_HOST=self.non_existent_tenant.domain_url
        )
        self.assertRaises(Http404, self.tm, request)

    def test_non_existent_tenant_to_default_schema_routing(self):
        """Route unrecognised hostnames to the 'public' tenant."""
        request = self.factory.get(
            self.url, HTTP_HOST=self.non_existent_tenant.domain_url
        )
        self.dtm(request)
        self.assertEqual(request.path_info, self.url)
        self.assertEqual(request.tenant, self.public_tenant)

    def test_non_existent_tenant_custom_middleware(self):
        """Route unrecognised hostnames to the 'test' tenant."""
        dtm = TestDefaultTenantMiddleware(lambda r: r)
        request = self.factory.get(
            self.url, HTTP_HOST=self.non_existent_tenant.domain_url
        )
        dtm(request)
        self.assertEqual(request.path_info, self.url)
        self.assertEqual(request.tenant, self.tenant)

    def test_non_existent_tenant_and_default_custom_middleware(self):
        """Route unrecognised hostnames to the 'missing' tenant."""
        dtm = MissingDefaultTenantMiddleware(lambda r: r)
        request = self.factory.get(
            self.url, HTTP_HOST=self.non_existent_tenant.domain_url
        )
        self.assertRaises(DisallowedHost, dtm, request)
