from django.conf import settings
from optparse import make_option
from django.core.management.base import NoArgsCommand, BaseCommand
from django.db import DEFAULT_DB_ALIAS
from django.core.management.base import CommandError
from django.db.models import get_apps, get_models
from django.core.management.commands.dumpdata import Command as DumpDataCommand
from django.db import connection
from tenant_schemas.utils import get_tenant_model, get_public_schema_name


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option("-s", "--schema", dest="schema_name"),
        make_option('--format', default='json', dest='format',
                    help='Specifies the output serialization format for fixtures.'),
        make_option('--indent', default=None, dest='indent', type='int',
                    help='Specifies the indent level to use when pretty-printing output'),
        make_option('--database', action='store', dest='database',
                    default=DEFAULT_DB_ALIAS, help='Nominates a specific database to dump '
                                                   'fixtures from. Defaults to the "default" database.'),
        make_option('-e', '--exclude', dest='exclude',action='append', default=[],
                    help='An appname or appname.ModelName to exclude (use multiple --exclude to exclude multiple apps/models).'),
        make_option('-n', '--natural', action='store_true', dest='use_natural_keys', default=False,
                    help='Use natural keys if they are available.'),
        make_option('-a', '--all', action='store_true', dest='use_base_manager', default=False,
                    help="Use Django's base manager to dump all models stored in the database, including those that would otherwise be filtered or modified by a custom manager."),
    )

    help = ("Output the contents of the database as a fixture of the given "
            "format (using each model's default manager unless --all is "
            "specified).")

    args = '[appname appname.ModelName ...]'

    def handle(self, *app_labels, **options):
        self.options = options
        self.app_labels = app_labels
        self.dump_tenant_data(options.get('schema_name'))


    def dump_tenant_data(self, schema_name=None):
        dumpdb_command = DumpDataCommand()
        if schema_name:
            print self.style.NOTICE("=== Running dumpdata for schema: %s" % schema_name)
            sync_tenant = get_tenant_model().objects.filter(schema_name=schema_name).get()
            connection.set_tenant(sync_tenant, include_public=True)
            dumpdb_command.execute(*self.app_labels, **self.options)
        else:
            public_schema_name = get_public_schema_name()
            tenant_schemas_count = get_tenant_model().objects.exclude(schema_name=public_schema_name).count()
            if not tenant_schemas_count:
                raise CommandError("No tenant schemas found")

            for tenant_schema in get_tenant_model().objects.exclude(schema_name=public_schema_name).all():
                print self.style.NOTICE("=== Running syncdb for schema %s" % tenant_schema.schema_name)
                try:
                    connection.set_tenant(tenant_schema, include_public=True)
                    dumpdb_command.execute(*self.app_labels, **self.options)
                except Exception as e:
                    print e
