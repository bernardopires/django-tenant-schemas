from django.core.management.commands.loaddata import Command as DataCommand
from django.db import connection

from tenant_schemas.management.commands import InteractiveTenantOption


class Command(InteractiveTenantOption, DataCommand):
    def handle(self, *args, **options):
        tenant = self.get_tenant_from_options_or_interactive(**options)
        connection.set_tenant(tenant)
        return super(Command, self).handle(*args, **options)
