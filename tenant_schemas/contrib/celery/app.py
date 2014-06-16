"""
Implementation of schema-aware celery application.
Usage:
    * Define a celery app using given `CeleryApp` class.

        ::
            from tenant_schemas.contrib.celery.app import CeleryApp

            os.environ.setdefault('DJANGO_SETTINGS_MODULE', '<your project settings>')

            app = CeleryApp()
            app.config_from_object('django.conf:settings')
            app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

      This assumes a fresh Celery 3.1.12 application. For previous versions,
      the key is to create a new `CeleryApp` instance that will be used to
      access task decorator from.

    * Replace your @task decorator with @app.task

        ::
            from django.db import connection
            from myproject.celery import app

            @app.task
            def my_task():
                print connection.schema_name

    * Run celery worker (`myproject.celery` is where you've defined the `app`
      variable)

        ::
            $ celery worker -A myproject.celery

    * Post registered task. The schema name will get automatically added to the
      task's arguments.

        ::
            from myproject.tasks import my_task
            my_task.delay()

The `TenantTask` class transparently inserts current connection's schema into
the task's kwargs. The schema name is then popped from the task's kwargs in
`task_prerun` signal handler, and the connection's schema is changed
accordingly.
"""

from __future__ import absolute_import

try:
    from celery import Celery
except ImportError:
    raise ImportError("celery is required to use tenant_schemas.contrib.celery")

from django.db import connection

from celery.signals import task_prerun


def switch_schema(kwargs, **kw):
    """ Switches schema of the task, before it has been run. """
    # Lazily load needed functions, as they import django model functions which
    # in turn load modules that need settings to be loaded and we can't
    # guarantee this module was loaded when the settings were ready.
    from tenant_schemas.utils import get_public_schema_name, get_tenant_model
    # Pop it from the kwargs since tasks don't except the additional kwarg.
    # This change is transparent to the system.
    schema = kwargs.pop('_schema_name', get_public_schema_name())
    connection.set_schema_to_public()
    tenant = get_tenant_model().objects.get(schema_name=schema)
    connection.set_tenant(tenant, include_public=True)

task_prerun.connect(switch_schema, sender=None,
                    dispatch_uid='tenant_schemas_switch_schema')


class CeleryApp(Celery):
    def create_task_cls(self):
        return self.subclass_with_self('tenant_schemas.contrib.celery.task:TenantTask',
                                        abstract=True, name='TenantTask',
                                        attribute='_app')
