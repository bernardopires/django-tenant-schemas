from unittest import TestCase
from django.db import connection
from tenant_schemas.utils import get_tenant_model

class TenantTestCase(TestCase):
    def setUp(self):
        # create a tenant
        self.tenant_domain = 'tenant.test.com'
        self.tenant = get_tenant_model()(domain_url=self.tenant_domain, schema_name='test')
        self.tenant.save()

        connection.set_tenant(self.tenant)
        super(TenantTestCase, self).setUp()