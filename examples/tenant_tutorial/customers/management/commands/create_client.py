from django.core.management.base import BaseCommand, CommandError
from customers.models import Client


class Command(BaseCommand):
    help = 'Create a new tenant client'

    def add_arguments(self, parser):
        parser.add_argument('schema', type=str, help='Schema name for the tenant')
        parser.add_argument('domain', type=str, help='Domain URL for the tenant')
        parser.add_argument('name', type=str, help='Name of the tenant')
        parser.add_argument('--description', type=str, help='Description of the tenant', default='')

    def handle(self, *args, **options):
        schema_name = options['schema']
        domain_url = options['domain']
        name = options['name']
        description = options['description']

        # Check if tenant with this schema already exists
        if Client.objects.filter(schema_name=schema_name).exists():
            raise CommandError(f'Tenant with schema "{schema_name}" already exists')

        # Check if tenant with this domain already exists
        if Client.objects.filter(domain_url=domain_url).exists():
            raise CommandError(f'Tenant with domain "{domain_url}" already exists')

        # Create the tenant
        client = Client(
            schema_name=schema_name,
            domain_url=domain_url,
            name=name,
            description=description
        )
        client.save()

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created tenant "{name}" with schema "{schema_name}" and domain "{domain_url}"'
            )
        )