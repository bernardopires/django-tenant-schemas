from django.db import connection
from django.utils.unittest import skipIf


from tenant_schemas.tests.models import Tenant, DummyModel
from tenant_schemas.tests.testcases import BaseTestCase

try:
    from .app import CeleryApp
except ImportError:
    app = None
else:
    app = CeleryApp('testapp')

    class CeleryConfig:
        CELERY_ALWAYS_EAGER = True
        CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

    app.config_from_object(CeleryConfig)

    @app.task
    def update_task(model_id, name):
        dummy = DummyModel.objects.get(pk=model_id)
        dummy.name = name
        dummy.save()

    @app.task
    def update_retry_task(model_id, name):
        if update_retry_task.request.retries:
            return update_task(model_id, name)

        # Don't throw the Retry exception.
        update_retry_task.retry(throw=False)


@skipIf(app is None, 'Celery is not available.')
class CeleryTasksTests(BaseTestCase):
    def setUp(self):
        super(CeleryTasksTests, self).setUp()
        self.tenant1 = Tenant(domain_url='test1', schema_name='test1')
        self.tenant1.save()

        self.tenant2 = Tenant(domain_url='test2', schema_name='test2')
        self.tenant2.save()

        connection.set_tenant(self.tenant1)
        self.dummy1 = DummyModel.objects.create(name='test1')

        connection.set_tenant(self.tenant2)
        self.dummy2 = DummyModel.objects.create(name='test2')

        connection.set_schema_to_public()

    def test_basic_model_update(self):
        # We should be in public schema where dummies don't exist.
        for dummy in self.dummy1, self.dummy2:
            # Test both async and local versions.
            with self.assertRaises(DummyModel.DoesNotExist):
                update_task.apply_async(args=(dummy.pk, 'updated-name'))

            with self.assertRaises(DummyModel.DoesNotExist):
                update_task.apply(args=(dummy.pk, 'updated-name'))

        connection.set_tenant(self.tenant1)
        update_task.apply_async(args=(self.dummy1.pk, 'updated-name'))

        model_count = DummyModel.objects.filter(name='updated-name').count()
        self.assertEqual(model_count, 1)

        connection.set_tenant(self.tenant2)
        model_count = DummyModel.objects.filter(name='updated-name').count()
        self.assertEqual(model_count, 0)

    def test_task_retry(self):
        # Schema name should persist through retry attempts.
        connection.set_tenant(self.tenant1)
        update_retry_task.apply_async(args=(self.dummy1.pk, 'updated-name'))

        model_count = DummyModel.objects.filter(name='updated-name').count()
        self.assertEqual(model_count, 1)
