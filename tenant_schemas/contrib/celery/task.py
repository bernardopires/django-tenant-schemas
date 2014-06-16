from celery.app.task import Task
from django.db import connection


class TenantTask(Task):
    """ Custom Task class that injects db schema currently used to the task's
        keywords so that the worker can use the same schema.
    """
    def _add_current_schema(self, kwds):
        kwds.setdefault('_schema_name', connection.schema_name)

    def apply_async(self, args=None, kwargs=None, *arg, **kw):
        kwargs = kwargs or {}
        self._add_current_schema(kwargs)
        return super(TenantTask, self).apply_async(args, kwargs, *arg, **kw)

    def apply(self, args=None, kwargs=None, *arg, **kw):
        kwargs = kwargs or {}
        self._add_current_schema(kwargs)
        return super(TenantTask, self).apply(args, kwargs, *arg, **kw)
