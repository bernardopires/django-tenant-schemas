from getpass import getpass
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.utils.six.moves import input

class Command(BaseCommand):
   
    help = "Wrapper around django commands for use with an individual tenant" 

    option_list = BaseCommand.option_list + (
        make_option(
            "--tenant", 
            dest = "tenant_schema",
            help = "specify tenant schema", 
        ),
    )

    def handle(self, command=None, target=None, *args, **options):
        from tenant_schemas.utils import get_tenant_model

        TenantModel = get_tenant_model()
        ContentType.objects.clear_cache()
        
        alltenants = TenantModel.objects.all()
        
        if not alltenants:
            raise CommandError("""There are no tenants in the system.
To learn how create a tenant, see:
https://django-tenant-schemas.readthedocs.org/en/latest/use.html#creating-a-tenant""")
        
        if options['tenant_schema']:
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

