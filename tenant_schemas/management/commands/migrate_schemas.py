import math
import django
import argparse

from django.core.management.commands.migrate import Command as MigrateCommand
from django.db.migrations.exceptions import MigrationSchemaMissing

from tenant_schemas.management.commands import SyncCommon
from tenant_schemas.migration_executors import get_executor
from tenant_schemas.utils import (
    get_public_schema_name,
    get_tenant_model,
    schema_exists,
)


def chunks(tenants, total_parts):
    """
    Iterates over tenants, returning each part, one at a time
    """
    tenants_per_chunk = int(math.ceil(float(len(tenants)) / total_parts))
    for i in range(0, len(tenants), tenants_per_chunk):
        yield tenants[i:i + tenants_per_chunk]


def greater_than_zero(astring):
    if not astring.isdigit():
        raise argparse.ArgumentTypeError('Needs to be a number')
    number = int(astring)
    if not number > 0:
        raise argparse.ArgumentTypeError('The number needs to be greated than zero')
    return number


class Command(SyncCommon):
    help = (
        "Updates database schema. Manages both apps with migrations and those without."
    )

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        command = MigrateCommand()
        command.add_arguments(parser)
        parser.add_argument('--part', action='store', dest='part', type=greater_than_zero, default=None,
                            help=('The part you want to process from the pieces (requires --of). '
                                  'Example: --part 2 --of 3'))
        parser.add_argument('--of', action='store', dest='total_parts', type=greater_than_zero, default=None,
                            help=('Splits the tenant schemas into specified number of pieces of equal size to '
                                  'then be proccessed in parts (requires --part). Example: --part 2 --of 3'))

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)

        required_together = (self.options['total_parts'], self.options['part'],)
        if any(required_together) and not all(required_together):
            raise Exception("--part and --of need to be used together.")
        elif all(required_together):
            if self.options['part'] > self.options['total_parts']:
                raise Exception("--of cannot be greater than --part.")
            elif self.sync_public:
                raise Exception("Cannot run public schema migrations along with --of and --part.")

        self.PUBLIC_SCHEMA_NAME = get_public_schema_name()

        executor = get_executor(codename=self.executor)(self.args, self.options)

        if self.sync_public and not self.schema_name:
            self.schema_name = self.PUBLIC_SCHEMA_NAME

        if self.sync_public:
            executor.run_migrations(tenants=[self.schema_name])
        if self.sync_tenant:
            if self.schema_name and self.schema_name != self.PUBLIC_SCHEMA_NAME:
                if not schema_exists(self.schema_name):
                    raise MigrationSchemaMissing(
                        'Schema "{}" does not exist'.format(self.schema_name)
                    )
                else:
                    tenants = [self.schema_name]
            else:
                tenants = (
                    get_tenant_model()
                    .objects.exclude(schema_name=get_public_schema_name())
                    .values_list('schema_name', flat=True).order_by('pk')
                )
                if self.options['total_parts'] and tenants:
                    tenant_parts = list(chunks(tenants, self.options['total_parts']))
                    try:
                        tenants = tenant_parts[self.options['part'] - 1]
                    except IndexError:
                        message = 'You have fewer tenants than parts. This part (%s) has nothing to do.\n'
                        self.stdout.write(message % self.options['part'])
                        return

            executor.run_migrations(tenants=tenants)
