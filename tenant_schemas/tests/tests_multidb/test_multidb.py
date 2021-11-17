import random
from django.conf import settings
from tenant_schemas.tests.models import Tenant, NonAutoSyncTenant
from tenant_schemas.tests.testcases import BaseTestCase
from tenant_schemas.utils import MultipleDBError
from tenant_schemas.utils import tenant_context, schema_context, schema_exists, get_tenant_model, get_public_schema_name
 

def get_all_dbs():
    result = []
    for db, val in settings.DATABASES.iteritems():
        result.append(db)
    return result
 

class MultiDBTenantDataAndSettingsTest(BaseTestCase):
    """
    Tests if the tenant model settings work properly and if data can be saved
    and persisted to different tenants in a multi-db environment.
    """
    @classmethod
    def setUpClass(cls):        
        settings.SHARED_APPS = ('tenant_schemas', )
        settings.TENANT_APPS = ('dts_test_app',
                                'django.contrib.contenttypes',
                                'django.contrib.auth', )
        settings.INSTALLED_APPS = settings.SHARED_APPS + settings.TENANT_APPS
        super(MultiDBTenantDataAndSettingsTest, cls).setUpClass()        
        for db in get_all_dbs():
            cls.sync_shared(db=db)
            Tenant(domain_url='test.com', schema_name=get_public_schema_name()).save(
                                                        verbosity=cls.get_verbosity(), 
                                                        using=db
                                                        )
    def  test_throw_exception_if_db_not_specified(self):
        """
        When saving a tenant without 'using' kwarg of save method throw
        MultiDBError 
        """
        tenant = Tenant(domain_url='something.test.com', schema_name='test')
        try:
            tenant.save(
                verbosity=BaseTestCase.get_verbosity())
        except Exception as e:
            self.assertTrue(isinstance(e, MultipleDBError))

    def  test_tenant_schema_creation_in_specified_db(self):
        """
        When saving a tenant using a db, its schema should be created in 
        that db
        """
        db = random.choice(get_all_dbs())
        tenant = Tenant(domain_url='something1.test.com', 
                                    schema_name='test1')
        tenant.save(
            verbosity=BaseTestCase.get_verbosity(),
            using=db)
        for d in get_all_dbs():
            if d == db:
                self.assertTrue(schema_exists(
                                        tenant.schema_name,
                                        db=d))
            else:
                self.assertFalse(schema_exists(
                                        tenant.schema_name,
                                        db=d))
