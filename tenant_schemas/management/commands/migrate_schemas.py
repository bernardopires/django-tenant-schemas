from django.db import connection
from tenant_schemas.management.commands import BaseTenantCommand
from tenant_schemas.models import TenantMixin
from tenant_schemas.utils import get_tenant_model

class Command(BaseTenantCommand):
    COMMAND_NAME = 'migrate'

    def handle(self, *args, **options):
        """
        Iterates a command over all registered schemata.
        """
        if options['schema_name']:
            # only run on a particular schema
            connection.set_schema_to_public()
            self.execute_command(get_tenant_model().objects.get(schema_name=options['schema_name']), self.COMMAND_NAME, *args, **options)
        else:
            # migration needs to be executed first on the public schema, else it might fail to select the tenants
            # if there's a modification on the tenant's table.
            public_tenant = TenantMixin(schema_name='public')
            self.execute_command(public_tenant, self.COMMAND_NAME, *args, **options)

            for tenant in get_tenant_model().objects.all():
                if tenant.schema_name != 'public':
                    self.execute_command(tenant, self.COMMAND_NAME, *args, **options)
