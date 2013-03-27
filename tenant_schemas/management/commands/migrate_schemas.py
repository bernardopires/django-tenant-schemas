from optparse import make_option
from django.core.management import CommandError
from django.core.management.base import NoArgsCommand
from django.db import connection
from django.conf import settings
from south import migration
from south.migration.base import Migrations
from tenant_schemas.utils import get_tenant_model, get_public_schema_name
from south.management.commands.migrate import Command as MigrateCommand


class Command(NoArgsCommand):
    option_list = MigrateCommand.option_list + (
        make_option('--tenant', action='store_true', dest='tenant', default=False,
                    help='Tells Django to populate only tenant applications.'),
        make_option('--shared', action='store_true', dest='shared', default=False,
                    help='Tells Django to populate only shared applications.'),
        make_option("-s", "--schema", dest="schema_name"),
    )

    def handle_noargs(self, **options):
        # todo: awful lot of duplication from sync_schemas
        sync_tenant = options.get('tenant')
        sync_public = options.get('shared')
        schema_name = options.get('schema_name')
        self.installed_apps = settings.INSTALLED_APPS
        self.options = options

        if sync_public and schema_name:
            raise CommandError("schema should only be used with the --tenant switch.")

        if not sync_public and not sync_tenant and not schema_name:
            # no options set, sync both
            sync_tenant = True
            sync_public = True

        if schema_name:
            if schema_name == get_public_schema_name():
                sync_public = True
            else:
                sync_tenant = True

        if hasattr(settings, 'TENANT_APPS'):
            self.tenant_apps = settings.TENANT_APPS
        if hasattr(settings, 'SHARED_APPS'):
            self.shared_apps = settings.SHARED_APPS

        if sync_public:
            self.migrate_public_apps()
        if sync_tenant:
            self.migrate_tenant_apps(schema_name)

    def _set_managed_apps(self, included_apps, excluded_apps):
        """ while sync_schemas works by setting which apps are managed, on south we set which apps should be ignored """
        ignored_apps = []
        if excluded_apps:
            for item in excluded_apps:
                if item not in included_apps:
                    ignored_apps.append(item)

        for app in ignored_apps:
            settings.SOUTH_MIGRATION_MODULES[app] = 'ignore'

    def _save_south_settings(self):
        self._old_south_modules = None
        if hasattr(settings, "SOUTH_MIGRATION_MODULES") and settings.SOUTH_MIGRATION_MODULES is not None:
            self._old_south_modules = settings.SOUTH_MIGRATION_MODULES.copy()
        else:
            settings.SOUTH_MIGRATION_MODULES = dict()

    def _restore_south_settings(self):
        settings.SOUTH_MIGRATION_MODULES = self._old_south_modules

    def _clear_south_cache(self):
        for mig in list(migration.all_migrations()):
            delattr(mig._application, "migrations")
        Migrations._clear_cache()

    def migrate_tenant_apps(self, schema_name=None):
        self._save_south_settings()

        apps = self.tenant_apps or self.installed_apps
        self._set_managed_apps(included_apps=apps, excluded_apps=self.shared_apps)

        migrate_command = MigrateCommand()
        if schema_name:
            print self.style.NOTICE("=== Running migrate for schema: %s" % schema_name)
            connection.set_schema_to_public()
            sync_tenant = get_tenant_model().objects.filter(schema_name=schema_name).get()
            connection.set_tenant(sync_tenant, include_public=False)
            migrate_command.execute(**self.options)
        else:
            public_schema_name = get_public_schema_name()
            tenant_schemas_count = get_tenant_model().objects.exclude(schema_name=public_schema_name).count()
            if not tenant_schemas_count:
                print self.style.NOTICE("No tenants found")

            for tenant_schema in get_tenant_model().objects.exclude(schema_name=public_schema_name).all():
                Migrations._dependencies_done = False  # very important, the dependencies need to be purged from cache
                print self.style.NOTICE("=== Running migrate for schema %s" % tenant_schema.schema_name)
                connection.set_tenant(tenant_schema, include_public=False)
                migrate_command.execute(**self.options)

        self._restore_south_settings()

    def migrate_public_apps(self):
        self._save_south_settings()

        apps = self.shared_apps or self.installed_apps
        self._set_managed_apps(included_apps=apps, excluded_apps=self.tenant_apps)

        print self.style.NOTICE("=== Running migrate for schema public")
        MigrateCommand().execute(**self.options)

        self._clear_south_cache()
        self._restore_south_settings()
