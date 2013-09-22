from django.core.management.base import CommandError

try:
    from south.management.commands import syncdb
except ImportError:
    from django.core.management.commands import syncdb


class Command(syncdb.Command):
    def handle_noargs(self, **options):
        raise CommandError("syncdb has been disabled, use sync_schemas instead. Please read the "
                           "documentation if you don't know why you shouldn't call syncdb directly!")