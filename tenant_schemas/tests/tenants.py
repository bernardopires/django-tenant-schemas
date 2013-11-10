from django.conf import settings
from django.db import connection
from django.test.testcases import TransactionTestCase
from tenant_schemas.tests.models import Tenant, NonAutoSyncTenant, DummyModel
from tenant_schemas.utils import (tenant_context, schema_exists,
                                  get_public_schema_name)


class TenantTestCase(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        settings.TENANT_APPS = ('tenant_schemas',
                                'django.contrib.contenttypes',
                                'django.contrib.auth', )

    def setUp(self):
        # settings needs some patching
        settings.TENANT_MODEL = 'tenant_schemas.Tenant'

        # add the public tenant
        self.public_tenant_domain = 'test.com'
        self.public_tenant = Tenant(domain_url=self.public_tenant_domain,
                                    schema_name='public')
        self.public_tenant.save()

        connection.set_schema_to_public()

    def tearDown(self):
        """
        Delete all tenant schemas. Tenant schema are not deleted
        automatically by django.
        """
        connection.set_schema_to_public()
        do_not_delete = [get_public_schema_name(), 'information_schema']
        cursor = connection.cursor()

        # Use information_schema.schemata instead of pg_catalog.pg_namespace in
        # utils.schema_exists, so that we only "see" schemas that we own
        cursor.execute('SELECT schema_name FROM information_schema.schemata')

        for row in cursor.fetchall():
            if not row[0].startswith('pg_') and row[0] not in do_not_delete:
                print("Deleting schema %s" % row[0])
                cursor.execute('DROP SCHEMA %s CASCADE' % row[0])

        Tenant.objects.all().delete()
        NonAutoSyncTenant.objects.all().delete()

    def test_tenant_schema_is_created(self):
        """
        when saving a tenant, it's schema should be created
        """
        tenant = Tenant(domain_url='something.test.com', schema_name='test')
        tenant.save()

        self.assertTrue(schema_exists(tenant.schema_name))

    def test_non_auto_sync_tenant(self):
        """
        when saving a tenant that has the flag auto_create_schema as
        False, the schema should not be created when saving the tenant
        """
        self.assertFalse(schema_exists('non_auto_sync_tenant'))

        tenant = NonAutoSyncTenant(domain_url='something.test.com',
                                   schema_name='test')
        tenant.save()

        self.assertFalse(schema_exists(tenant.schema_name))

    def test_sync_tenant(self):
        """
        when editing an existing tenant, all data should be kept
        """
        tenant = Tenant(domain_url='something.test.com', schema_name='test')
        tenant.save()

        # go to tenant's path
        connection.set_tenant(tenant)

        # add some data
        DummyModel(name="Schemas are").save()
        DummyModel(name="awesome!").save()

        # edit tenant
        connection.set_schema_to_public()
        tenant.domain_url = 'example.com'
        tenant.save()

        connection.set_tenant(tenant)

        # test if data is still there
        self.assertEquals(DummyModel.objects.count(), 2)

    def test_switching_search_path(self):
        dummies_tenant1_count, dummies_tenant2_count = 0, 0

        tenant1 = Tenant(domain_url='something.test.com',
                         schema_name='tenant1')
        tenant1.save()

        connection.set_schema_to_public()
        tenant2 = Tenant(domain_url='example.com', schema_name='tenant2')
        tenant2.save()

        # go to tenant1's path
        connection.set_tenant(tenant1)

        # add some data
        DummyModel(name="Schemas are").save()
        DummyModel(name="awesome!").save()
        dummies_tenant1_count = DummyModel.objects.count()

        # switch temporarily to tenant2's path
        with tenant_context(tenant2):
            # add some data
            DummyModel(name="Man,").save()
            DummyModel(name="testing").save()
            DummyModel(name="is great!").save()
            dummies_tenant2_count = DummyModel.objects.count()

        # we should be back to tenant1's path, test what we have
        self.assertEqual(DummyModel.objects.count(), dummies_tenant1_count)

        # switch back to tenant2's path
        with tenant_context(tenant2):
            self.assertEqual(DummyModel.objects.count(), dummies_tenant2_count)
