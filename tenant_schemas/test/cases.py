from django.core.management import call_command
from django.db import connection, DEFAULT_DB_ALIAS
from django.test import TransactionTestCase
from django.utils.unittest.case import TestCase
from tenant_schemas.utils import get_tenant_model

class TenantTestCase(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        # create a tenant
        tenant_domain = 'tenant.test.com'
        cls.tenant = get_tenant_model()(domain_url=tenant_domain, schema_name='test')
        cls.tenant.save()

        connection.set_tenant(cls.tenant)