import functools
import multiprocessing

from django.conf import settings

from tenant_schemas.migration_executors.base import MigrationExecutor


def _run_migration_alias(args, options, tenants, allow_atomic=True):
    """
    Alias for run_migration method that allows the method to be called in a
    multiprocessing pool
    """
    parallel_executor = ParallelExecutor(args, options)
    parallel_executor.run_migration(tenants, allow_atomic=allow_atomic)
    return


class ParallelExecutor(MigrationExecutor):
    codename = 'parallel'

    def run_tenant_migrations(self, tenants):
        if tenants:
            processes = getattr(settings, 'TENANT_PARALLEL_MIGRATION_MAX_PROCESSES', 2)
            chunks = getattr(settings, 'TENANT_PARALLEL_MIGRATION_CHUNKS', 2)

            from django.db import connection

            connection.close()
            connection.connection = None

            run_migrations_p = functools.partial(
                _run_migration_alias,
                self.args,
                self.options,
                allow_atomic=False
            )
            p = multiprocessing.Pool(processes=processes)
            p.map(run_migrations_p, tenants, chunks)
