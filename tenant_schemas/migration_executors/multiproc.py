import functools
import multiprocessing

from django.conf import settings

from .base import MigrationExecutor, run_migrations


class MultiprocessingExecutor(MigrationExecutor):
    codename = 'multiprocessing'

    def run_migrations(self, tenants=None):
        tenants = tenants or []

        if self.PUBLIC_SCHEMA_NAME in tenants:
            run_migrations(self.args, self.options, self.PUBLIC_SCHEMA_NAME)
            tenants.pop(tenants.index(self.PUBLIC_SCHEMA_NAME))

        if tenants:
            processes = getattr(settings, 'TENANT_MULTIPROCESSING_MAX_PROCESSES', 2)
            chunks = getattr(settings, 'TENANT_MULTIPROCESSING_CHUNKS', 1)

            from django.db import connection

            connection.close()
            connection.connection = None

            migrate = functools.partial(run_migrations, self.args, self.options, allow_atomic=False)
            p = multiprocessing.Pool(processes=processes)
            p.map(migrate, tenants, chunks)
