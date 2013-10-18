from django.core.management.base import NoArgsCommand, CommandError


class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        raise CommandError("migrate has been disabled, use migrate_schemas instead. Please read the "
                           "documentation if you don't know why you shouldn't call migrate directly!")