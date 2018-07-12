from tenant_schemas.migration_executors.base import MigrationExecutor


class StandardExecutor(MigrationExecutor):
    codename = 'standard'

    def run_tenant_migrations(self, tenants):
        for schema_name in tenants:
            self.run_migration(schema_name)
