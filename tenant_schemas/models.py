from django.conf import settings
from django.db import models, connection, transaction
from tenant_schemas.postgresql_backend.base import _check_identifier
from django.core.management import call_command
from tenant_schemas.signals import post_schema_sync
from tenant_schemas.utils import django_is_in_test_mode, schema_exists
from .utils import get_public_schema_name


class TenantMixin(models.Model):
    auto_create_schema = True # set this flag to false on a parent class if
                              # you dont want the schema to be automatically
                              # created upon save.

    domain_url = models.CharField(max_length=128, unique=True)
    schema_name = models.CharField(max_length=63)

    class Meta:
        abstract = True

    def save(self, verbosity = 1, *args, **kwargs):
        if connection.get_schema() != get_public_schema_name():
            raise Exception("Can't update tenant outside the public schema. Current schema is %s." % connection.get_schema())

        is_new = self.pk is None
        super(TenantMixin, self).save(*args, **kwargs)

        if is_new and self.auto_create_schema:
            self.create_schema(check_if_exists=True, verbosity=verbosity)
            post_schema_sync.send(sender=TenantMixin, tenant=self)

        transaction.commit_unless_managed()

    def create_schema(self, check_if_exists=False, sync_schema=True, verbosity=1):
        """
        Creates the schema 'schema_name' for this tenant. Optionally checks if the schema
        already exists before creating it. Returns true if the schema was created, false
        otherwise.
        """

        # safety check
        _check_identifier(self.schema_name)
        cursor = connection.cursor()

        if check_if_exists and schema_exists(self.schema_name):
            return False

        # create the schema
        cursor.execute('CREATE SCHEMA %s' % self.schema_name)

        if sync_schema:
            call_command('sync_schemas',
                         schema_name=self.schema_name,
                         tenant=True,
                         public=False,
                         interactive=False,  # don't ask to create an admin user
                         migrate_all=True,  # migrate all apps directly to last version
                         verbosity=verbosity,
                         )

            # fake all migrations
            if 'south' in settings.INSTALLED_APPS and not django_is_in_test_mode():
                call_command('migrate_schemas', fake=True, schema_name=self.schema_name, verbosity=verbosity)

        return True
