from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from tenant_schemas.postgresql_backend.base import _check_identifier
from tenant_schemas.utils import get_tenant_model

class Command(BaseCommand):
    help = "Manages the postgresql schemata."
    
    def handle(self, *unused_args, **unused_options):
        self.create_schemas()

    def create_schemas(self):
        """
        Go through all tenants and create all schemas that
        do not already exist in the database. 
        """
        cursor = connection.cursor()
        cursor.execute('SELECT schema_name FROM information_schema.schemata')
        existing_schemata = [row[0] for row in cursor.fetchall()]

        for tenant in get_tenant_model().objects.all():
            _check_identifier(tenant.schema_name)
        
            if tenant.schema_name not in existing_schemata:
                sql = 'CREATE SCHEMA %s' % tenant.schema_name
                print sql
                cursor.execute(sql)
                transaction.commit_unless_managed()
