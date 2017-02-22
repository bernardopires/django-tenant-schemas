import sys

from django.core.management import color
from django.core.management.base import OutputWrapper
from django.core.management.commands.migrate import Command as MigrateCommand
from django.db import connection, transaction

from tenant_schemas.utils import get_public_schema_name


def run_migrations(args, options, schema_name):
    style = color.color_style()

    def style_function(message):
        return '[{schema_name}] {message}'.format(
            schema_name=style.NOTICE(schema_name),
            message=message
        )

    connection.set_schema(schema_name)

    stdout = OutputWrapper(sys.stdout)
    stdout.style_func = style_function
    stderr = OutputWrapper(sys.stderr)
    stderr.style_func = style_function

    if int(options.get('verbosity', 1)) >= 1:
        stdout.write(style.NOTICE("=== Running migrate"))

    with transaction.atomic():
        MigrateCommand().execute(*args, **options)

    connection.set_schema_to_public()


class BaseMigrationExecutor(object):
    name = None

    def __init__(self, args, options):
        self.args = args
        self.options = options

    def run_public_migrations(self):
        run_migrations(self.args, self.options, get_public_schema_name())

    def run(self, tenants):
        raise NotImplementedError
