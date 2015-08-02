import django
from django.core.management import call_command
from django.db import connection

from tenant_schemas.utils import get_tenant_model
from tenant_schemas.utils import get_public_schema_name


class TenantRequestFactoryMixin(object):

    def __init__(self, **defaults):
        super(TenantRequestFactoryMixin, self).__init__(**defaults)
        # we will deduct the tenant from the db backend, which will be
        # initialized by the test case class setup method, before the factory
        # initialization
        self.tenant = connection.tenant

    def get(self, path, data={}, **extra):
        if 'HTTP_HOST' not in extra:
            extra['HTTP_HOST'] = self.tenant.domain_url

        return super(TenantRequestFactoryMixin, self).get(path, data, **extra)

    def post(self, path, data={}, **extra):
        if 'HTTP_HOST' not in extra:
            extra['HTTP_HOST'] = self.tenant.domain_url

        return super(TenantRequestFactoryMixin, self).post(path, data, **extra)

    def patch(self, path, data={}, **extra):
        if 'HTTP_HOST' not in extra:
            extra['HTTP_HOST'] = self.tenant.domain_url

        return super(TenantRequestFactoryMixin, self).patch(path, data, **extra)

    def put(self, path, data={}, **extra):
        if 'HTTP_HOST' not in extra:
            extra['HTTP_HOST'] = self.tenant.domain_url

        return super(TenantRequestFactoryMixin, self).put(path, data, **extra)

    def delete(self, path, data='', content_type='application/octet-stream',
               **extra):
        if 'HTTP_HOST' not in extra:
            extra['HTTP_HOST'] = self.tenant.domain_url

        return super(TenantRequestFactoryMixin, self).delete(path, data, **extra)


class TenantTestCaseMixin(object):
    @classmethod
    def setUpClass(cls):
        cls.sync_shared()
        tenant_domain = 'tenant.test.com'
        cls.tenant = get_tenant_model()(domain_url=tenant_domain, schema_name='test')
        cls.tenant.save(verbosity=0)  # todo: is there any way to get the verbosity from the test command here?

        connection.set_tenant(cls.tenant)

    @classmethod
    def tearDownClass(cls):
        connection.set_schema_to_public()
        cls.tenant.delete()

        cursor = connection.cursor()
        cursor.execute('DROP SCHEMA test CASCADE')

    @classmethod
    def sync_shared(cls):
        if django.VERSION >= (1, 7, 0):
            call_command('migrate_schemas',
                         schema_name=get_public_schema_name(),
                         interactive=False,
                         verbosity=0)
        else:
            call_command('sync_schemas',
                         schema_name=get_public_schema_name(),
                         tenant=False,
                         public=True,
                         interactive=False,
                         migrate_all=True,
                         verbosity=0,
                         )
