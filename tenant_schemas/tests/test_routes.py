import unittest

import six
from django.conf import settings
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


@unittest.skipIf(six.PY2, "Unexpectedly failing only on Python 2.7")
class RoutesTestCase(BaseTestCase):
    @classmethod
    def setUpClass(cls):
        super(RoutesTestCase, cls).setUpClass()
        settings.SHARED_APPS = ("tenant_schemas",)
        settings.TENANT_APPS = (
            "dts_test_app",
            "django.contrib.contenttypes",
            "django.contrib.auth",
        )
        settings.INSTALLED_APPS = settings.SHARED_APPS + settings.TENANT_APPS
        cls.sync_shared()
        cls.public_tenant = Tenant(
            domain_url="test.com", schema_name=get_public_schema_name()
        )
        cls.public_tenant.save(verbosity=BaseTestCase.get_verbosity())

    def setUp(self):
        super(RoutesTestCase, self).setUp()
        self.factory = RequestFactory()
        self.tm = TenantMiddleware()
        self.dtm = DefaultTenantMiddleware()

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
        self.tm.process_request(request)
        self.assertEquals(request.path_info, self.url)
        self.assertEquals(request.tenant, self.tenant)

    def test_public_schema_routing(self):
        request = self.factory.get(self.url, HTTP_HOST=self.public_tenant.domain_url)
        self.tm.process_request(request)
        self.assertEquals(request.path_info, self.url)
        self.assertEquals(request.tenant, self.public_tenant)

    def test_non_existent_tenant_routing(self):
        """Raise 404 for unrecognised hostnames."""
        request = self.factory.get(
            self.url, HTTP_HOST=self.non_existent_tenant.domain_url
        )
        self.assertRaises(Http404, self.tm.process_request, request)

    def test_non_existent_tenant_to_default_schema_routing(self):
        """Route unrecognised hostnames to the 'public' tenant."""
        request = self.factory.get(
            self.url, HTTP_HOST=self.non_existent_tenant.domain_url
        )
        self.dtm.process_request(request)
        self.assertEquals(request.path_info, self.url)
        self.assertEquals(request.tenant, self.public_tenant)

    def test_non_existent_tenant_custom_middleware(self):
        """Route unrecognised hostnames to the 'test' tenant."""
        dtm = TestDefaultTenantMiddleware()
        request = self.factory.get(
            self.url, HTTP_HOST=self.non_existent_tenant.domain_url
        )
        dtm.process_request(request)
        self.assertEquals(request.path_info, self.url)
        self.assertEquals(request.tenant, self.tenant)

    def test_non_existent_tenant_and_default_custom_middleware(self):
        """Route unrecognised hostnames to the 'missing' tenant."""
        dtm = MissingDefaultTenantMiddleware()
        request = self.factory.get(
            self.url, HTTP_HOST=self.non_existent_tenant.domain_url
        )
        self.assertRaises(DisallowedHost, dtm.process_request, request)
