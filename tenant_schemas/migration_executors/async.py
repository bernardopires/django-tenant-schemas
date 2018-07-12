from django.conf import settings
from celery import group

from tenant_schemas.migration_executors.base import MigrationExecutor


class CeleryExecutor(MigrationExecutor):
    codename = 'async'

    def run_migrations(self, tenants):
        is_interactive = getattr(settings, 'TENANT_INTERACTIVE_MIGRATION', False)
        self.options['interactive'] = is_interactive
        super(CeleryExecutor, self).run_migrations(tenants)

    def run_tenant_migrations(self, tenants):
        from tenant_schemas.tasks import run_schema_migration
        tenant_migrations = group(
            run_schema_migration.s(self.args, self.options, schema_name)
            for schema_name in tenants
        )
        result = tenant_migrations.apply_async()
        unsuccessfully_migrated_schemas = filter(lambda schema_name: schema_name is not None, result.get())
        self.logger.info('Completed migrations for private tenants: {} correct, {} incorrect ({})'.format(
            len(tenants) - len(unsuccessfully_migrated_schemas), len(unsuccessfully_migrated_schemas),
            ", ".join(str(x) for x in unsuccessfully_migrated_schemas)))
