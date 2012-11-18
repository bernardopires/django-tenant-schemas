from django.core.management import call_command
from django.db import connection
from tenant_schemas.management.commands import BaseTenantCommand

class Command(BaseTenantCommand):
    COMMAND_NAME = 'syncdb'

    def execute_command(self, tenant, command_name, *args, **options):
        verbosity = int(options.get('verbosity'))

        if verbosity >= 1:
            print
            print self.style.NOTICE("=== Switching to schema '")\
                  + self.style.SQL_TABLE(tenant.schema_name)\
                  + self.style.NOTICE("' then calling %s:" % command_name)

        # sets the schema for the connection
        connection.set_tenant(tenant, include_public = False)

        # call the original command with the args it knows
        call_command(command_name, *args, **options)
