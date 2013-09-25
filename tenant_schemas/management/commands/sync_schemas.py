import itertools
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import get_apps, get_models
from django.db.models.signals import post_syncdb
from django.contrib.sites import models as site_app
from django.contrib.sites.management import create_default_site
if "south" in settings.INSTALLED_APPS:
    from south.management.commands.syncdb import Command as SyncdbCommand
else:
    from django.core.management.commands.syncdb import Command as SyncdbCommand
from django.db import connection

from tenant_schemas.utils import get_tenant_model, get_public_schema_name
from tenant_schemas.management.common import SyncCommon


class Command(SyncCommon):
    help = "Sync schemas based on TENANT_APPS and SHARED_APPS settings"
    option_list = SyncdbCommand.option_list + SyncCommon.option_list

    def handle_noargs(self, **options):
        super(Command, self).handle_noargs(**options)

        if "south" in settings.INSTALLED_APPS:
            self.options["migrate"] = False

        # save original settings
        for model in get_models(include_auto_created=True):
            setattr(model._meta, 'was_managed', model._meta.managed)

        # Django sites app would insert the default example.com at every new schema creation
        # into the public schema, so we just disconnect that signal before emitted
        if self.schema_name and site_app.Site in connection.shared_models:
            post_syncdb.disconnect(create_default_site, site_app)

        ContentType.objects.clear_cache()

        if self.sync_public:
            self.sync_public_apps()
        if self.sync_tenant:
            self.sync_tenant_apps(self.schema_name)

        # restore settings
        for model in get_models(include_auto_created=True):
            model._meta.managed = model._meta.was_managed

    def _set_managed_apps(self, included_apps):
        """ sets which apps are managed by syncdb """
        for model in get_models(include_auto_created=True):
            model._meta.managed = False

        verbosity = int(self.options.get('verbosity'))
        for app_model in get_apps():
            app_name = app_model.__name__.replace('.models', '')
            if hasattr(app_model, 'models') and app_name in included_apps:
                for model in get_models(app_model, include_auto_created=True):
                    model._meta.managed = True and model._meta.was_managed
                    if model._meta.managed and verbosity >= 3:
                        self._notice("=== Include Model: %s: %s" % (app_name, model.__name__))

    def _sync_tenant(self, tenant):
        self._notice("=== Running syncdb for schema: %s" % tenant.schema_name)
        connection.set_tenant(tenant, include_public=False)
        SyncdbCommand().execute(**self.options)

    def sync_tenant_apps(self, schema_name=None):
        apps = self.tenant_apps or self.installed_apps
        self._set_managed_apps(apps)
        self.options['load_initial_data'] = False

        if schema_name:
            tenant = get_tenant_model().objects.get(schema_name=schema_name)
            self._sync_tenant(tenant)
        else:
            all_tenants = get_tenant_model().objects.exclude(schema_name=get_public_schema_name())
            if not all_tenants:
                self._notice("No tenants found!")

            for tenant in all_tenants:
                self._sync_tenant(tenant)

    def sync_public_apps(self):
        apps = self.shared_apps or self.installed_apps
        self._set_managed_apps(apps)
        self._notice("=== Running syncdb for schema public")
        SyncdbCommand().execute(**self.options)
