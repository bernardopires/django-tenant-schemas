from tenant_schemas.management.commands import BaseSchemataCommand

class Command(BaseSchemataCommand):
    COMMAND_NAME = 'migrate'
