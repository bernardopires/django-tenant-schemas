from django.conf import settings
from optparse import make_option
from django.core.management.base import NoArgsCommand
from django.db import DEFAULT_DB_ALIAS
from django.core.management.base import CommandError
from django.db.models import get_apps, get_models, get_model
if "south" in settings.INSTALLED_APPS:
    from south.management.commands.syncdb import Command as SyncdbCommand
else:
    from django.core.management.commands.syncdb import Command as SyncdbCommand
from django.db import connection
from tenant_schemas.utils import get_tenant_model, get_public_schema_name


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--noinput', action='store_false', dest='interactive', default=True,
                    help='Tells Django to NOT prompt the user for input of any kind.'),
        make_option('--tenant', action='store_true', dest='tenant', default=False,
                    help='Tells Django to populate only tenant applications.'),
        make_option('--shared', action='store_true', dest='shared', default=False,
                    help='Tells Django to populate only shared applications.'),
        make_option("-s", "--schema", dest="schema_name"),
        make_option('--database', action='store', dest='database', default=DEFAULT_DB_ALIAS,
                    help='Nominates a database to synchronize. Defaults to the "default" database.'),
    )

    def handle_noargs(self, **options):
        sync_tenant = options.get('tenant')
        sync_public = options.get('shared')
        schema_name = options.get('schema_name')
        installed_apps = settings.INSTALLED_APPS
        self.options = options

        if "south" in settings.INSTALLED_APPS:
            self.options["migrate"] = False

        if sync_public and schema_name:
            raise CommandError("schema should only be used with the --tenant switch.")
        if not hasattr(settings, 'TENANT_APPS') and sync_tenant:
            raise CommandError("No setting found for TENANT_APPS")
        if not hasattr(settings, 'SHARED_APPS') and sync_public:
            raise CommandError("No setting found for SHARED_APPS")

        # save original settings
        for model in get_models(include_auto_created=True):
            setattr(model._meta, 'was_managed', model._meta.managed)

        if not sync_public and not sync_tenant:
            # no options set, sync both
            sync_tenant = True
            sync_public = True

        if hasattr(settings, 'TENANT_APPS'):
            tenant_apps = settings.TENANT_APPS
        if hasattr(settings, 'SHARED_APPS'):
            shared_apps = settings.SHARED_APPS

        if sync_public:
            self.sync_public_apps(shared_apps or installed_apps)
        if sync_tenant:
            self.sync_tenant_apps(tenant_apps or installed_apps, schema_name)

        # restore settings
        for model in get_models(include_auto_created=True):
            model._meta.managed = model._meta.was_managed

    def _set_managed_apps(self, included_apps):
        for model in get_models(include_auto_created=True):
            model._meta.managed = False

        verbosity = int(self.options.get('verbosity'))
        for app_model in get_apps():
            app_name = app_model.__name__.replace('.models', '')
            if hasattr(app_model, 'models') and app_name in included_apps:
                for model in get_models(app_model, include_auto_created=True):
                    model._meta.managed = True and model._meta.was_managed
                    if model._meta.managed and verbosity >= 3:
                        print self.style.NOTICE("=== Include Model: %s: %s" % (app_name, model.__name__))

    def sync_tenant_apps(self, apps, schema_name=None):
        self._set_managed_apps(apps)
        syncdb_command = SyncdbCommand()
        if schema_name:
            print self.style.NOTICE("=== Running syncdb for schema: %s" % schema_name)
            sync_tenant = get_tenant_model().objects.filter(schema_name=schema_name).get()
            connection.set_tenant(sync_tenant, include_public=False)
            syncdb_command.execute(**self.options)
        else:
            public_schema_name = get_public_schema_name()
            tenant_schemas_count = get_tenant_model().objects.exclude(schema_name=public_schema_name).count()
            if not tenant_schemas_count:
                raise CommandError("No tenant schemas found")

            for tenant_schema in get_tenant_model().objects.exclude(schema_name=public_schema_name).all():
                print self.style.NOTICE("=== Running syncdb for schema %s" % tenant_schema.schema_name)
                try:
                    connection.set_tenant(tenant_schema, include_public=False)
                    syncdb_command.execute(**self.options)
                except Exception as e:
                    print e

    def sync_public_apps(self, apps):
        self._set_managed_apps(apps)
        print self.style.NOTICE("=== Running syncdb for schema public")
        SyncdbCommand().execute(**self.options)