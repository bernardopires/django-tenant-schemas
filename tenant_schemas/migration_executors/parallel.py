import functools
import multiprocessing

from django.conf import settings

from tenant_schemas.migration_executors.base import (
    BaseMigrationExecutor, run_migrations)


class ParallelExecutor(BaseMigrationExecutor):
    name = 'parallel'

    def run(self, tenants):
        if tenants:
            processes = getattr(settings, 'MIGRATION_PARALLEL_MAX_PROCESSES', 2)
            chunks = getattr(settings, 'MIGRATION_PARALLEL_CHUNKS', 2)

            run_migrations_p = functools.partial(
                run_migrations,
                self.args,
                self.options
            )
            p = multiprocessing.Pool(processes=processes)
            p.map(run_migrations_p, tenants, chunks)
            p.close()
            p.join()
