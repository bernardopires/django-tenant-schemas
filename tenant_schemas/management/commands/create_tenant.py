from optparse import make_option
from django.core import exceptions
from django.core.management.base import BaseCommand
from django.utils.encoding import force_str
from django.utils.six.moves import input
from django.conf import settings
from django.db.utils import IntegrityError
from tenant_schemas.utils import get_tenant_model


class Command(BaseCommand):
    help = 'Create a tenant'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.option_list = BaseCommand.option_list + (
            make_option('--schema-name', help='Specifies the schema name for the tenant (e.g. "new_tenant").'),
            make_option('--domain-url', help='Specifies the domain_url for the tenant (e.g. "new-tenant.localhost").'),
        )

    def handle(self, *args, **options):
        schema_name = options.get('schema_name', None)
        domain_url = options.get('domain_url', None)

        if schema_name:
            if not domain_url:
                base_domain = getattr(settings, 'TENANT_BASE_DOMAIN', 'localhost')
                domain_url='{0}.{1}'.format(schema_name, base_domain)

            tenant = self.store_tenant(
                domain_url=domain_url,
                schema_name=schema_name
            )
            if not tenant:
                schema_name = None

        while schema_name is None:
            if not schema_name:
                input_msg = 'Schema name'
                schema_name = input(force_str('%s: ' % input_msg))

            base_domain = getattr(settings, 'TENANT_BASE_DOMAIN', 'localhost')
            default_domain_url='{0}.{1}'.format(schema_name, base_domain)

            while domain_url is None:
                if not domain_url:
                    input_msg = 'Domain url'
                    input_msg = "%s (leave blank to use '%s')" % (input_msg, default_domain_url)
                    domain_url = input(force_str('%s: ' % input_msg)) or default_domain_url

            tenant = self.store_tenant(
                domain_url=domain_url,
                schema_name=schema_name
            )

            if not tenant:
                name = None
                continue


    def store_tenant(self, domain_url, schema_name):
        try:
            client = get_tenant_model().objects.create(
                domain_url=domain_url,
                schema_name=schema_name
            )
            client.save()
            return client
        except exceptions.ValidationError as e:
            self.stderr.write("Error: %s" % '; '.join(e.messages))
            name = None
            return False
        except IntegrityError as e:
            self.stderr.write("Error: We've already got a tenant with that name or property.")
            return False
