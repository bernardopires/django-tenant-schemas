import django

from django.core.management.commands.migrate import Command as MigrateCommand

from tenant_schemas.management.commands import SyncCommon
from tenant_schemas.utils import (
    get_tenant_model, get_public_schema_name, schema_exists)
from tenant_schemas.migration_executors import get_executor

if django.VERSION >= (1, 9, 0):
    from django.db.migrations.exceptions import MigrationSchemaMissing
else:
    class MigrationSchemaMissing(django.db.utils.DatabaseError):
        pass


class Command(SyncCommon):
    PUBLIC_SCHEMA_NAME = None
    schema_name = None
    help = ('Updates database schema. '
            'Manages both apps with migrations and those without.')

    def __init__(self, stdout=None, stderr=None, no_color=False):
        """
        Changes the option_list to use the
        options from the wrapped migrate command.
        """
        if django.VERSION <= (1, 10, 0):
            self.option_list += MigrateCommand.option_list
        super(Command, self).__init__(stdout, stderr, no_color)

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        command = MigrateCommand()
        command.add_arguments(parser)

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)
        self.PUBLIC_SCHEMA_NAME = get_public_schema_name()

        executor = get_executor(name=self.executor)(self.args, self.options)

        if self.sync_public and not self.schema_name:
            self.schema_name = self.PUBLIC_SCHEMA_NAME

        if self.sync_public:
            executor.run_public_migrations()
        if self.sync_tenant:
            if self.schema_name and self.schema_name != self.PUBLIC_SCHEMA_NAME:
                if not schema_exists(self.schema_name):
                    raise MigrationSchemaMissing(
                        'Schema "{}" does not exist'.format(
                            self.schema_name))
                else:
                    tenants = [self.schema_name]
            else:
                tenants = get_tenant_model().objects.exclude(
                    schema_name=get_public_schema_name()
                ).values_list(
                    'schema_name',
                    flat=True
                )

            if tenants:
                executor.run(tenants=tenants)
