import math
import django
import argparse

from django.core.management.commands.migrate import Command as MigrateCommand

from tenant_schemas.management.commands import SyncCommon
from tenant_schemas.migration_executors import get_executor
from tenant_schemas.utils import get_public_schema_name, get_tenant_model, schema_exists

if django.VERSION >= (1, 9, 0):
    from django.db.migrations.exceptions import MigrationSchemaMissing
else:
    class MigrationSchemaMissing(django.db.utils.DatabaseError):
        pass


def chunks(l, n):
    for i in range(0, len(l), int(math.ceil(len(l) / n))):
        yield l[i:i + n]


def greater_than_x(min_number, message):
    def wrapper(astring):
        if not astring.isdigit():
            raise argparse.ArgumentTypeError('Needs to be a number')
        number = int(astring)
        if not number > min_number:
            raise argparse.ArgumentTypeError(message)
        return number
    return wrapper


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
        parser.add_argument('--part', action='store', dest='migration_part',
                            type=greater_than_x(1, 'The number needs to be greated than one'), default=None,
                            help=('Splits the tenant schemas into pieces of equal parts to then be proccessed in '
                                  'parts (requires --of).'))
        parser.add_argument('--of', action='store', dest='migration_part_of',
                            type=greater_than_x(0, 'The number needs to be greated than zero'), default=None,
                            help='The part you want to process from the pieces (requires --part).')

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)

        required_together = (self.options['migration_part'], self.options['migration_part_of'],)
        if any(required_together) and not all(required_together):
            raise Exception("--part and --of need to be used together.")
        elif all(required_together):
            if self.options['migration_part_of'] > self.options['migration_part']:
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
                    raise MigrationSchemaMissing('Schema "{}" does not exist'.format(
                        self.schema_name))
                else:
                    tenants = [self.schema_name]
            else:
                tenants = get_tenant_model().objects.exclude(schema_name=get_public_schema_name()) \
                                            .order_by('pk').values_list('schema_name', flat=True)
                if self.options['migration_part'] and self.options['migration_part'] > 1 and tenants:
                    tenant_parts = list(chunks(tenants, self.options['migration_part'] - 1))
                    tenants = tenant_parts[self.options['migration_part_of'] - 1]
            executor.run_migrations(tenants=tenants)
