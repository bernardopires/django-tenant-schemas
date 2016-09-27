from django.conf import settings
from django.contrib.auth.models import User
from django.db import connection, transaction
from dts_test_app.models import DummyModel, ModelWithFkToPublicUser

from tenant_schemas.migration_executors import get_executor
from tenant_schemas.test.cases import TenantTestCase
from tenant_schemas.tests.testcases import BaseTestCase
from tenant_schemas.utils import get_public_schema_name, get_tenant_model, schema_context, schema_exists, tenant_context


class TenantDataAndSettingsTest(BaseTestCase):
    """
    Tests if the tenant model settings work properly and if data can be saved
    and persisted to different tenants.
    """
    @classmethod
    def setUpClass(cls):
        super(TenantDataAndSettingsTest, cls).setUpClass()
        settings.SHARED_APPS = ('tenant_schemas',
                                'customers')
        settings.TENANT_APPS = ('dts_test_app',
                                'django.contrib.contenttypes',
                                'django.contrib.auth',)
        settings.INSTALLED_APPS = settings.SHARED_APPS + settings.TENANT_APPS

        cls.sync_shared()
        cls.public_tenant = get_tenant_model()(domain_url='test.com', schema_name=get_public_schema_name())
        cls.public_tenant.save(verbosity=cls.get_verbosity())

    @classmethod
    def tearDownClass(cls):
        cls.public_tenant.delete()
        super(TenantDataAndSettingsTest, cls).tearDownClass()

    def setUp(self):
        self.created = []
        super(TenantDataAndSettingsTest, self).setUp()

    def tearDown(self):
        from tenant_schemas.models import TenantMixin

        connection.set_schema_to_public()

        for c in self.created:
            if isinstance(c, TenantMixin):
                c.delete(force_drop=True)
            else:
                c.delete()

        super(TenantDataAndSettingsTest, self).tearDown()

    def test_tenant_schema_is_created(self):
        """
        When saving a tenant, it's schema should be created.
        """
        tenant = get_tenant_model()(domain_url='something.test.com', schema_name='test')
        tenant.save(verbosity=BaseTestCase.get_verbosity())

        self.assertTrue(schema_exists(tenant.schema_name))

        self.created = [tenant]

    def test_tenant_schema_is_created_atomically(self):
        """
        When saving a tenant, it's schema should be created.
        This should work in atomic transactions too.
        """
        executor = get_executor()
        tenant = get_tenant_model()
        schema_name = 'test'

        @transaction.atomic()
        def atomically_create_tenant():
            t = tenant(schema_name=schema_name)
            t.save()

            self.created = [t]

        if executor == 'simple':
            atomically_create_tenant()

            self.assertTrue(schema_exists(schema_name))
        elif executor == 'multiprocessing':
            # Unfortunately, it's impossible for the multiprocessing executor
            # to assert atomic transactions when creating a tenant
            with self.assertRaises(transaction.TransactionManagementError):
                atomically_create_tenant()

    def test_non_auto_sync_tenant(self):
        """
        When saving a tenant that has the flag auto_create_schema as
        False, the schema should not be created when saving the tenant.
        """
        tenant = get_tenant_model()(domain_url='something.test.com', schema_name='test')
        tenant.auto_create_schema = False
        tenant.save(verbosity=BaseTestCase.get_verbosity())

        self.assertFalse(schema_exists(tenant.schema_name))

        self.created = [tenant]

    def test_sync_tenant(self):
        """
        When editing an existing tenant, all data should be kept.
        """
        tenant = get_tenant_model()(domain_url='something.test.com', schema_name='test')
        tenant.save(verbosity=BaseTestCase.get_verbosity())

        # go to tenant's path
        connection.set_tenant(tenant)

        # add some data
        DummyModel(name="Schemas are").save()
        DummyModel(name="awesome!").save()

        # edit tenant
        connection.set_schema_to_public()
        tenant.domain_url = 'example.com'
        tenant.save(verbosity=BaseTestCase.get_verbosity())

        connection.set_tenant(tenant)

        # test if data is still there
        self.assertEquals(DummyModel.objects.count(), 2)

        self.created = [tenant]

    def test_switching_search_path(self):
        tenant1 = get_tenant_model()(domain_url='something.test.com', schema_name='tenant1')
        tenant1.save(verbosity=BaseTestCase.get_verbosity())

        connection.set_schema_to_public()

        tenant2 = get_tenant_model()(domain_url='example.com', schema_name='tenant2')
        tenant2.save(verbosity=BaseTestCase.get_verbosity())

        # go to tenant1's path
        connection.set_tenant(tenant1)

        # add some data, 2 DummyModels for tenant1
        DummyModel(name="Schemas are").save()
        DummyModel(name="awesome!").save()

        # switch temporarily to tenant2's path
        with tenant_context(tenant2):
            # add some data, 3 DummyModels for tenant2
            DummyModel(name="Man,").save()
            DummyModel(name="testing").save()
            DummyModel(name="is great!").save()

        # we should be back to tenant1's path, test what we have
        self.assertEqual(2, DummyModel.objects.count())

        # switch back to tenant2's path
        with tenant_context(tenant2):
            self.assertEqual(3, DummyModel.objects.count())

        self.created = [tenant2, tenant1]

    def test_switching_tenant_without_previous_tenant(self):
        tenant = get_tenant_model()(domain_url='something.test.com', schema_name='test')
        tenant.save(verbosity=BaseTestCase.get_verbosity())

        connection.tenant = None
        with tenant_context(tenant):
            DummyModel(name="No exception please").save()

        connection.tenant = None
        with schema_context(tenant.schema_name):
            DummyModel(name="Survived it!").save()

        self.created = [tenant]


class BaseSyncTest(BaseTestCase):
    """
    Tests if the shared apps and the tenant apps get synced correctly
    depending on if the public schema or a tenant is being synced.
    """
    MIGRATION_TABLE_SIZE = 1

    SHARED_APPS = ('tenant_schemas',
                   'customers',  # 1 tables
                   'django.contrib.auth',  # 6 tables
                   'django.contrib.contenttypes', )  # 1 table
    TENANT_APPS = ('django.contrib.sessions', )

    @classmethod
    def setUpClass(cls):
        super(BaseSyncTest, cls).setUpClass()
        cls.INSTALLED_APPS = cls.SHARED_APPS + cls.TENANT_APPS

        settings.SHARED_APPS = cls.SHARED_APPS
        settings.TENANT_APPS = cls.TENANT_APPS
        settings.INSTALLED_APPS = cls.INSTALLED_APPS

        cls.available_apps = cls.INSTALLED_APPS

    def setUp(self):
        super(BaseSyncTest, self).setUp()
        # Django calls syncdb by default for the test database, but we want
        # a blank public schema for this set of tests.
        connection.set_schema_to_public()
        with connection.cursor() as cursor:
            cursor.execute('DROP SCHEMA %s CASCADE; CREATE SCHEMA %s;'
                           % (get_public_schema_name(), get_public_schema_name(), ))

        self.sync_shared()


class TenantSyncTest(BaseSyncTest):
    """
    Tests if the shared apps and the tenant apps get synced correctly
    depending on if the public schema or a tenant is being synced.
    """
    MIGRATION_TABLE_SIZE = 1

    def test_shared_apps_does_not_sync_tenant_apps(self):
        """
        Tests that if an app is in SHARED_APPS, it does not get synced to
        the a tenant schema.
        """
        shared_tables = self.get_tables_list_in_schema(get_public_schema_name())
        self.assertEqual(1 + 6 + 1 + self.MIGRATION_TABLE_SIZE, len(shared_tables))
        self.assertNotIn('django_session', shared_tables)

    def test_tenant_apps_does_not_sync_shared_apps(self):
        """
        Tests that if an app is in TENANT_APPS, it does not get synced to
        the public schema.
        """
        tenant = get_tenant_model()(domain_url='arbitrary.test.com', schema_name='test')
        tenant.save(verbosity=BaseTestCase.get_verbosity())

        tenant_tables = self.get_tables_list_in_schema(tenant.schema_name)
        self.assertEqual(1 + self.MIGRATION_TABLE_SIZE, len(tenant_tables))
        self.assertIn('django_session', tenant_tables)

        connection.set_schema_to_public()
        tenant.delete(force_drop=True)


class TestSyncTenantsWithAuth(BaseSyncTest):
    SHARED_APPS = ('tenant_schemas',
                   'customers',            # 1 tables
                   'django.contrib.auth',  # 6 tables
                   'django.contrib.contenttypes',  # 1 table
                   'django.contrib.sessions',)  # 1 table
    TENANT_APPS = ('django.contrib.sessions',)  # 1 table

    def _pre_setup(self):
        self.sync_shared()
        super(TestSyncTenantsWithAuth, self)._pre_setup()

    def test_tenant_apps_and_shared_apps_can_have_the_same_apps(self):
        """
        Tests that both SHARED_APPS and TENANT_APPS can have apps in common.
        In this case they should get synced to both tenant and public schemas.
        """
        tenant = get_tenant_model()(schema_name='test', domain_url='arbitrary.test.com')
        tenant.save()

        shared_tables = self.get_tables_list_in_schema(get_public_schema_name())
        tenant_tables = self.get_tables_list_in_schema(tenant.schema_name)
        self.assertEqual(1 + 6 + 1 + 1 + self.MIGRATION_TABLE_SIZE, len(shared_tables))
        self.assertIn('django_session', shared_tables)
        self.assertEqual(1 + self.MIGRATION_TABLE_SIZE, len(tenant_tables))
        self.assertIn('django_session', tenant_tables)


class TestSyncTenantsNoAuth(BaseSyncTest):
    SHARED_APPS = ('tenant_schemas',
                   'customers',  # 1 tables
                   'django.contrib.contenttypes',)  # 1 table
    TENANT_APPS = ('django.contrib.sessions',)  # 1 table

    def test_content_types_is_not_mandatory(self):
        """
        Tests that even if content types is in SHARED_APPS, it's
        not required in TENANT_APPS.
        """
        tenant = get_tenant_model()(schema_name='test', domain_url='something.test.com')
        tenant.save()

        shared_tables = self.get_tables_list_in_schema(get_public_schema_name())
        tenant_tables = self.get_tables_list_in_schema(tenant.schema_name)
        self.assertEqual(1 + 1 + self.MIGRATION_TABLE_SIZE, len(shared_tables))
        self.assertIn('django_session', tenant_tables)
        self.assertEqual(1 + self.MIGRATION_TABLE_SIZE, len(tenant_tables))
        self.assertIn('django_session', tenant_tables)


class SharedAuthTest(BaseTestCase):
    def setUp(self):
        super(SharedAuthTest, self).setUp()

        settings.SHARED_APPS = ('tenant_schemas',
                                'customers',
                                'django.contrib.auth',
                                'django.contrib.contenttypes',)
        settings.TENANT_APPS = ('dts_test_app',)
        settings.INSTALLED_APPS = settings.SHARED_APPS + settings.TENANT_APPS
        self.sync_shared()
        self.public_tenant = get_tenant_model()(schema_name=get_public_schema_name(), domain_url='test.com')
        self.public_tenant.save()

        # Create a tenant
        self.tenant = get_tenant_model()(schema_name='tenant', domain_url='tenant.test.com')
        self.tenant.save()
        # Create some users
        with schema_context(get_public_schema_name()):  # this could actually also be executed inside a tenant
            self.user1 = User(username='arbitrary-1', email="arb1@test.com")
            self.user1.save()
            self.user2 = User(username='arbitrary-2', email="arb2@test.com")
            self.user2.save()

        # Create instances on the tenant that point to the users on public
        with tenant_context(self.tenant):
            self.d1 = ModelWithFkToPublicUser(user=self.user1)
            self.d1.save()
            self.d2 = ModelWithFkToPublicUser(user=self.user2)
            self.d2.save()

    def tearDown(self):
        connection.set_schema_to_public()
        self.public_tenant.delete()
        self.tenant.delete(force_drop=True)

        super(SharedAuthTest, self).tearDown()

    def test_cross_schema_constraint_gets_created(self):
        """
        Tests that a foreign key constraint gets created even for cross schema references.
        """
        sql = """
            SELECT
                tc.constraint_name, tc.table_name, kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM
                information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
            WHERE constraint_type = 'FOREIGN KEY' AND tc.table_name=%s
        """
        cursor = connection.cursor()
        cursor.execute(sql, (ModelWithFkToPublicUser._meta.db_table,))
        fk_constraints = cursor.fetchall()
        self.assertEqual(1, len(fk_constraints))

        # The foreign key should reference the primary key of the user table
        fk = fk_constraints[0]
        self.assertEqual(User._meta.db_table, fk[3])
        self.assertEqual('id', fk[4])

    def test_direct_relation_to_public(self):
        """
        Tests that a forward relationship through a foreign key to public from a model inside TENANT_APPS works.
        """
        with tenant_context(self.tenant):
            self.assertEqual(User.objects.get(pk=self.user1.id),
                             ModelWithFkToPublicUser.objects.get(pk=self.d1.id).user)
            self.assertEqual(User.objects.get(pk=self.user2.id),
                             ModelWithFkToPublicUser.objects.get(pk=self.d2.id).user)

    def test_reverse_relation_to_public(self):
        """
        Tests that a reverse relationship through a foreign keys to public from a model inside TENANT_APPS works.
        """
        with tenant_context(self.tenant):
            users = User.objects.all().select_related().order_by('id')
            self.assertEqual(ModelWithFkToPublicUser.objects.get(pk=self.d1.id),
                             users[0].modelwithfktopublicuser_set.all()[:1].get())
            self.assertEqual(ModelWithFkToPublicUser.objects.get(pk=self.d2.id),
                             users[1].modelwithfktopublicuser_set.all()[:1].get())


class TenantTestCaseTest(BaseTestCase, TenantTestCase):
    """
    Tests that the tenant created inside TenantTestCase persists on
    all functions.
    """

    def test_tenant_survives_after_method1(self):
        # There is one tenant in the database, the one created by TenantTestCase
        self.assertEquals(1, get_tenant_model().objects.all().count())

    def test_tenant_survives_after_method2(self):
        # The same tenant still exists even after the previous method call
        self.assertEquals(1, get_tenant_model().objects.all().count())
