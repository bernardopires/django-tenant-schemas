from optparse import make_option, NO_DEFAULT
from collections import OrderedDict
import django
from django.apps import apps
from django.core.management.commands.migrate import Command as MigrateCommand
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.conf import settings

from tenant_schemas.utils import (get_tenant_model, get_public_schema_name,
                                  schema_exists)


class MigrateSchemasCommand(BaseCommand):
    help = "Wrapper around django commands for use with an individual tenant"

    option_list = (
        make_option('--tenant', action='store_true', dest='tenant', default=False,
                    help='Tells Django to populate only tenant applications.'),
        make_option('--shared', action='store_true', dest='shared', default=False,
                    help='Tells Django to populate only shared applications.'),
        make_option("-s", "--schema", dest="schema_name"),
    )


    def run_from_argv(self, argv):
        """
        Changes the option_list to use the options from the wrapped command.
        Adds schema parameter to specify which schema will be used when
        executing the wrapped command.
        """
        self.option_list += MigrateCommand.option_list
        super(MigrateSchemasCommand, self).run_from_argv(argv)

    def handle(self, *args, **options):
        self.non_tenant_schemas = settings.PG_EXTRA_SEARCH_PATHS + ['public']
        self.sync_tenant = options.get('tenant')
        self.sync_public = options.get('shared')
        self.schema_name = options.get('schema_name')
        self.args = args
        self.options = options
        self.PUBLIC_SCHEMA_NAME = get_public_schema_name()

        if self.schema_name:
            if self.sync_public:
                raise CommandError("schema should only be used "
                                   "with the --tenant switch.")
            elif self.schema_name == self.PUBLIC_SCHEMA_NAME:
                self.sync_public = True
            else:
                self.sync_tenant = True
        elif not self.sync_public and not self.sync_tenant:
            # no options set, sync both
            self.sync_tenant = True
            self.sync_public = True

        if self.sync_public and not self.schema_name:
            self.schema_name = self.PUBLIC_SCHEMA_NAME

        if self.sync_public:
            self.run_migrations(self.schema_name, settings.SHARED_APPS)
        if self.sync_tenant:
            if self.schema_name and \
                    (self.schema_name != self.PUBLIC_SCHEMA_NAME):
                # Make sure the tenant exists and the schema belongs to
                # a tenant; We don't want to sync to extensions schema by
                # mistake
                if not schema_exists(self.schema_name):
                    raise RuntimeError('Schema "{}" does not exist'.format(
                        self.schema_name))
                elif self.schema_name in self.non_tenant_schemas:
                    raise RuntimeError(
                        'Schema "{}" does not belong to any tenant'.format(
                            self.schema_name))
                else:
                    self.run_migrations(self.schema_name, settings.TENANT_APPS)
            else:
                all_tenants = get_tenant_model().objects.exclude(
                    schema_name=get_public_schema_name())
                for tenant in all_tenants:
                    self.run_migrations(tenant.schema_name, settings.TENANT_APPS)

    def run_migrations(self, schema_name, included_apps):
        self._notice("=== Running migrate for schema %s" % schema_name)
        connection.set_schema(schema_name, include_public=False)
        apps.app_configs = OrderedDict()
        apps.clear_cache()
        apps.set_installed_apps(included_apps)

        command = MigrateCommand()

        defaults = {}
        for opt in MigrateCommand.option_list:
            if opt.dest in self.options:
                defaults[opt.dest] = self.options[opt.dest]
            elif opt.default is NO_DEFAULT:
                defaults[opt.dest] = None
            else:
                defaults[opt.dest] = opt.default

        command.execute(*self.args, **defaults)

        connection.set_schema('public', include_public=True)
        apps.app_configs = OrderedDict()
        apps.clear_cache()
        apps.set_installed_apps(settings.SHARED_APPS)

    def _notice(self, output):
        self.stdout.write(self.style.NOTICE(output))


if django.VERSION >= (1, 7, 0):
    Command = MigrateSchemasCommand
else:
    from .legacy.migrate_schemas import Command
