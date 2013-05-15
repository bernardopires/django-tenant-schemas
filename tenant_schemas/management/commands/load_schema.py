from optparse import make_option
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS
from django.core.management.base import CommandError
from django.core.management.commands.loaddata import Command as LoadDataCommand
from django.db import connection
from tenant_schemas.utils import get_tenant_model, get_public_schema_name


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option("-s", "--schema", dest="schema_name"),
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a specific database to load '
                'fixtures into. Defaults to the "default" database.'),
        make_option('--ignorenonexistent', '-i', action='store_true', dest='ignore',
            default=False, help='Ignores entries in the serialized data for fields'
                                ' that do not currently exist on the model.'),
    )

    help = 'Installs the named fixture(s) in the database.'
    args = "fixture [fixture ...]"

    def handle(self, *app_labels, **options):
        self.options = options
        self.app_labels = app_labels
        self.load_tenant_data(options.get('schema_name'))

    def load_tenant_data(self, schema_name=None):
        loaddb_command = LoadDataCommand()
        if schema_name:
            print self.style.NOTICE("=== Running loaddata for schema: %s" % schema_name)
            sync_tenant = get_tenant_model().objects.filter(schema_name=schema_name).get()
            connection.set_tenant(sync_tenant, include_public=True)
            loaddb_command.execute(*self.app_labels, **self.options)
        else:
            public_schema_name = get_public_schema_name()
            tenant_schemas_count = get_tenant_model().objects.exclude(schema_name=public_schema_name).count()
            if not tenant_schemas_count:
                raise CommandError("No tenant schemas found")

            for tenant_schema in get_tenant_model().objects.exclude(schema_name=public_schema_name).all():
                print self.style.NOTICE("=== Running syncdb for schema %s" % tenant_schema.schema_name)
                try:
                    connection.set_tenant(tenant_schema, include_public=True)
                    loaddb_command.execute(*self.app_labels, **self.options)
                except Exception as e:
                    print e
