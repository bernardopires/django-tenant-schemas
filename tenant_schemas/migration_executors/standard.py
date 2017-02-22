from tenant_schemas.migration_executors.base import (
    BaseMigrationExecutor, run_migrations)


class StandardExecutor(BaseMigrationExecutor):
    name = 'standard'

    def run(self, tenants):
        for schema_name in tenants:
            run_migrations(self.args, self.options, schema_name)
