import django

from django.conf import settings
from django.core.management.commands.migrate import Command as MigrateCommand
from django.db import connection

from tenant_schemas.management.commands import SyncCommon
from tenant_schemas.utils import get_tenant_model, get_public_schema_name, schema_exists

if django.VERSION >= (1, 9, 0):
    from django.db.migrations.exceptions import MigrationSchemaMissing
else:
    class MigrationSchemaMissing(django.db.utils.DatabaseError):
        pass


class Command(SyncCommon):
    help = "Updates database schema. Manages both apps with migrations and those without."

    def __init__(self, stdout=None, stderr=None, no_color=False):
        """
        Changes the option_list to use the options from the wrapped migrate command.
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

        if self.sync_public and not self.schema_name:
            self.schema_name = self.PUBLIC_SCHEMA_NAME

        if self.sync_public:
            self.run_migrations(self.schema_name, settings.SHARED_APPS)
        if self.sync_tenant:
            if self.schema_name and self.schema_name != self.PUBLIC_SCHEMA_NAME:
                if not schema_exists(self.schema_name):
                    raise MigrationSchemaMissing('Schema "{}" does not exist'.format(
                        self.schema_name))
                else:
                    self.run_migrations(self.schema_name, settings.TENANT_APPS)
            else:
                all_tenants = get_tenant_model().objects.exclude(schema_name=get_public_schema_name())
                for tenant in all_tenants:
                    self.run_migrations(tenant.schema_name, settings.TENANT_APPS)

    def run_migrations(self, schema_name, included_apps):
        if int(self.options.get('verbosity', 1)) >= 1:
            self._notice("=== Running migrate for schema %s" % schema_name)

        if not schema_exists(schema_name):
            raise MigrationSchemaMissing('Schema "{}" does not exist'.format(
                schema_name))

        connection.set_schema(schema_name)
        command = MigrateCommand()
        command.execute(*self.args, **self.options)
        connection.set_schema_to_public()

    def _notice(self, output):
        self.stdout.write(self.style.NOTICE(output))
