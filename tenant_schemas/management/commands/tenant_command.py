from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
from tenant_schemas.management.commands import InteractiveTenantOption


class Command(InteractiveTenantOption, BaseCommand):
    help = "Wrapper around django commands for use with an individual tenant"

    def handle(self, *args, **options):
        tenant = self.get_tenant_from_options_or_interactive(**options)
        connection.set_tenant(tenant)

        call_command(*args, **options)
