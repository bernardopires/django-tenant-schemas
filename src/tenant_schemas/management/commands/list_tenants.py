import csv
import sys

from django.core.management import BaseCommand
from tenant_schemas.utils import get_tenant_model


class Command(BaseCommand):
    def handle(self, *args, **options):
        columns = ('schema_name', 'domain_url')

        TenantModel = get_tenant_model()
        all_tenants = TenantModel.objects.values_list(*columns)

        out = csv.writer(sys.stdout, dialect=csv.excel_tab)
        for tenant in all_tenants:
            out.writerow(tenant)
