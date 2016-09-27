from django.core.management import call_command
from django.db import connection
from django.test import TransactionTestCase

from tenant_schemas.utils import get_public_schema_name, get_tenant_model


class TenantTestCase(TransactionTestCase):
    def setup_tenant(self, tenant):
        """
        Add any additional setting to the tenant before it get saved. This is required if you have
        required fields.
        :param tenant:
        :return:
        """
        pass

    def setUp(self):
        self.sync_shared()
        self.tenant = get_tenant_model()(schema_name='test', domain_url='tenant.test.com')
        self.setup_tenant(self.tenant)
        self.tenant.save(verbosity=0)  # todo: is there any way to get the verbosity from the test command here?

        connection.set_tenant(self.tenant)

    def tearDown(self):
        connection.set_schema_to_public()
        self.tenant.delete(force_drop=True)

    @classmethod
    def sync_shared(cls):
        call_command('migrate_schemas',
                     schema_name=get_public_schema_name(),
                     interactive=False,
                     verbosity=0)
