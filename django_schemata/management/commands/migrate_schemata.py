from django_schemata.management.commands.sync_schemata import BaseSchemataCommand

# Uses the twin command base code for the actual iteration.

class Command(BaseSchemataCommand):
    COMMAND_NAME = 'migrate'
