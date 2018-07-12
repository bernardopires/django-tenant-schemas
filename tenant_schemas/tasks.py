from celery import shared_task
from tenant_schemas.migration_executors.base import MigrationExecutor


@shared_task(ignore_result=False)
def run_schema_migration(args, options, schema_name):
    migration_executor = MigrationExecutor(args, options)
    try:
        migration_executor.run_migration(schema_name)
    except Exception:
        return schema_name
