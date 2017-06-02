from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from tenant_schemas.utils import get_public_schema_name, get_tenant_model

ALLOWED_TEST_DOMAIN = '.test.com'


class TenantTestCase(TestCase):
    @classmethod
    def add_allowed_test_domain(cls):
        # ALLOWED_HOSTS is a special setting of Django setup_test_environment so we can't modify it with helpers
        if ALLOWED_TEST_DOMAIN not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS += [ALLOWED_TEST_DOMAIN]

    @classmethod
    def remove_allowed_test_domain(cls):
        if ALLOWED_TEST_DOMAIN in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.remove(ALLOWED_TEST_DOMAIN)

    @classmethod
    def setUpClass(cls):
        cls.sync_shared()
        cls.add_allowed_test_domain()
        tenant_domain = 'tenant.test.com'
        cls.tenant = get_tenant_model()(domain_url=tenant_domain, schema_name='test')
        cls.tenant.save(verbosity=0)  # todo: is there any way to get the verbosity from the test command here?

        connection.set_tenant(cls.tenant)

    @classmethod
    def tearDownClass(cls):
        connection.set_schema_to_public()
        cls.tenant.delete()

        cls.remove_allowed_test_domain()
        cursor = connection.cursor()
        cursor.execute('DROP SCHEMA IF EXISTS test CASCADE')

    @classmethod
    def sync_shared(cls):
        call_command('migrate_schemas',
                     schema_name=get_public_schema_name(),
                     interactive=False,
                     verbosity=0)


class FastTenantTestCase(TenantTestCase):
    @classmethod
    def setUpClass(cls):
        cls.sync_shared()
        cls.add_allowed_test_domain()
        tenant_domain = 'tenant.test.com'

        TenantModel = get_tenant_model()
        try:
            cls.tenant = TenantModel.objects.get(domain_url=tenant_domain, schema_name='test')
        except:
            cls.tenant = TenantModel(domain_url=tenant_domain, schema_name='test')
            cls.tenant.save(verbosity=0)

        connection.set_tenant(cls.tenant)

    @classmethod
    def tearDownClass(cls):
        connection.set_schema_to_public()
        cls.remove_allowed_test_domain()
