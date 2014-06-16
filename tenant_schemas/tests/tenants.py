from django.db import connection

from tenant_schemas.tests.models import Tenant, NonAutoSyncTenant, DummyModel
from tenant_schemas.tests.testcases import BaseTestCase
from tenant_schemas.utils import tenant_context, schema_context, schema_exists


class TenantTestCase(BaseTestCase):
    def tearDown(self):
        super(TenantTestCase, self).tearDown()
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

    def test_switching_tenant_without_previous_tenant(self):
        tenant = Tenant(domain_url='something.test.com', schema_name='test')
        tenant.save()

        connection.tenant = None
        with tenant_context(tenant):
            DummyModel(name="No exception please").save()

        connection.tenant = None
        with schema_context(tenant.schema_name):
            DummyModel(name="Survived it!").save()
