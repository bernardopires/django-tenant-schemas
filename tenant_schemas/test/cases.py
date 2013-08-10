from django.db import connection
from django.test import TransactionTestCase
from tenant_schemas.utils import get_tenant_model


class TenantTestCase(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        # create a tenant
        tenant_domain = 'tenant.test.com'
        cls.tenant = get_tenant_model()(domain_url=tenant_domain, schema_name='test')
        cls.tenant.save(verbosity=0)  # todo: is there any way to get the verbosity from the test command here?

        connection.set_tenant(cls.tenant)

    @classmethod
    def tearDownClass(cls):
        # delete tenant
        connection.set_schema_to_public()
        cls.tenant.delete()

        cursor = connection.cursor()
        cursor.execute('DROP SCHEMA test CASCADE')