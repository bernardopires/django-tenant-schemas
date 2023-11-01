import shlex

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection
from tenant_schemas.management.commands import InteractiveTenantOption


class Command(InteractiveTenantOption, BaseCommand):
    requires_system_checks = []
    help = "Wrapper around django commands for use with an individual tenant"

    def handle(self, command, schema_name, *args, **options):
        tenant = self.get_tenant_from_options_or_interactive(
            schema_name=schema_name, **options
        )
        connection.set_tenant(tenant)

        # allow passing a command as string including parameters
        #  eg. `./manage.py tenant_command -s tenant "test_command --foo 123"`
        parsed_command = shlex.split(command)
        call_command(*parsed_command, *args, **options)
