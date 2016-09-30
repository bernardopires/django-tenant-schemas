import sys

from django.core.management.commands.migrate import Command as MigrateCommand
from django.db import transaction

from tenant_schemas.utils import get_public_schema_name


def run_migrations(args, options, schema_name, allow_atomic=True):
    from django.core.management import color
    from django.core.management.base import OutputWrapper
    from django.db import connection

    style = color.color_style()
    stdout = OutputWrapper(sys.stdout)
    stderr = OutputWrapper(sys.stderr)
    connection.set_schema(schema_name)
    if int(options.get('verbosity', 1)) >= 1:
        stdout.write(style.NOTICE('Running migrate for schema %s' % schema_name))

    MigrateCommand(stdout=stdout, stderr=stderr).execute(*args, **options)

    try:
        transaction.commit()
        connection.close()
        connection.connection = None
    except transaction.TransactionManagementError:
        if not allow_atomic:
            raise
        # We are in atomic transaction, don't close connections
        pass

    connection.set_schema_to_public()


class MigrationExecutor(object):
    codename = None

    def __init__(self, args, options):
        self.args = args
        self.options = options
        self.PUBLIC_SCHEMA_NAME = get_public_schema_name()

    def run_migrations(self, tenants=None):
        raise NotImplementedError
