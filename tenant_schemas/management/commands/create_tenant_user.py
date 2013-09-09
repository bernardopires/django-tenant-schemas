from getpass import getpass

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.utils.six.moves import input

class Command(BaseCommand):

    def handle(self, *args, **options):
        from tenant_schemas.utils import get_tenant_model, remove_www_and_dev, get_public_schema_name, clean_tenant_url

        TenantModel = get_tenant_model()
        ContentType.objects.clear_cache()
        
        alltenants = TenantModel.objects.all()
        
        if not alltenants:
            raise CommandError("There are no tenants, so you can't create a user!")
        
        tenstrings = ["%s - %s" % (t.pk, t.domain_url,) for t in alltenants]
        
        tenant_id = input("%s\nPick a tenant id to create a user account for: " % ('\n'.join(tenstrings),))
        
        if int(tenant_id) not in [t.pk for t in alltenants]:
            raise CommandError("Invalid tenant id, '%s'" % (tenant_id,))

        tenant = TenantModel.objects.get(pk=tenant_id)
        connection.set_tenant(tenant)
        
        username = input("Username: ")
        email = input("Email: ")
        password = getpass()
        superuser = input("Superuser? [y/N]: ")
       
        if superuser == 'y':
            User.objects.create_superuser(username=username, email=email, password=password)
        else:
            User.objects.create_user(username=username, email=email, password=password)

