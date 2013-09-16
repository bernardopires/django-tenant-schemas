from optparse import make_option
from django.conf import settings
from django.core.management.base import NoArgsCommand

class SyncCommon(NoArgsCommand):
    option_list = (
        make_option('--tenant', action='store_true', dest='tenant', default=False,
                    help='Tells Django to populate only tenant applications.'),
        make_option('--shared', action='store_true', dest='shared', default=False,
                    help='Tells Django to populate only shared applications.'),
        make_option("-s", "--schema", dest="schema_name"),
    )

    def handle_noargs(self, **options):
        self.sync_tenant = options.get('tenant')
        self.sync_public = options.get('shared')
        self.schema_name = options.get('schema_name')
        self.installed_apps = settings.INSTALLED_APPS
        self.options = options

        if self.schema_name:
            if self.sync_public:
                raise CommandError("schema should only be used with the --tenant switch.")
            elif self.schema_name == get_public_schema_name():
                self.sync_public = True
            else:
                self.sync_tenant = True
        elif not self.sync_public and not self.sync_tenant:
            # no options set, sync both
            self.sync_tenant = True
            self.sync_public = True

        if hasattr(settings, 'TENANT_APPS'):
            self.tenant_apps = settings.TENANT_APPS
        if hasattr(settings, 'SHARED_APPS'):
            self.shared_apps = settings.SHARED_APPS

    def _notice(self, output):
        self.stdout.write(self.style.NOTICE(output))
