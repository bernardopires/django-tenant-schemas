import sys
from getpass import getpass
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command, get_commands, load_command_class
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.utils.six.moves import input

class Command(BaseCommand):
   
    help = "Wrapper around django commands for use with an individual tenant" 

    __parent_command = None
    __parent_command_app = None

    option_list = (
        make_option(
            "--schema", 
            dest = "tenant_schema",
            help = "specify tenant schema", 
        ),
    )

    def __init__(self):
        allcommands = get_commands()
        try:
            self.__parent_command = sys.argv[2]
            self.__parent_command_app = allcommands[self.__parent_command]
        except KeyError:
            raise CommandError("Could not find command: %s" % (self.__parent_command,))
        super(Command, self).__init__()

    def get_parent_command(self):
        return load_command_class(self.__parent_command_app, self.__parent_command)

    def create_parser(self, prog_name, subcommand):
        """
        Create and return the ``OptionParser`` which will be used to
        parse the arguments to this command.

        """
        parent_command = self.get_parent_command()
        parent_command.option_list += self.option_list
        return parent_command.create_parser(prog_name, subcommand)

    def handle(self, command=None, target=None, *args, **options):
        from tenant_schemas.utils import get_tenant_model

        TenantModel = get_tenant_model()
        ContentType.objects.clear_cache()
        
        alltenants = TenantModel.objects.all()
        
        if not alltenants:
            raise CommandError("""There are no tenants in the system.
To learn how create a tenant, see:
https://django-tenant-schemas.readthedocs.org/en/latest/use.html#creating-a-tenant""")
        
        if options.get('tenant_schema'):
            tenant_schema = options['tenant_schema']
        else:
            while True:
                tenant_schema = input("Enter Tenant Schema ('?' to list schemas): ")
                if tenant_schema == '?':
                    print '\n'.join(["%s - %s" % (t.schema_name, t.domain_url,) for t in alltenants])
                else:
                    break

        if tenant_schema not in [t.schema_name for t in alltenants]:
            raise CommandError("Invalid tenant schema, '%s'" % (tenant_schema,))

        tenant = TenantModel.objects.get(schema_name=tenant_schema)
        connection.set_tenant(tenant)

        call_command(command, target, *args, **options)

