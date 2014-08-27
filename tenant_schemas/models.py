from django.conf import settings
from django.db import models, connection, transaction
from django.core.management import call_command
from tenant_schemas.postgresql_backend.base import _check_schema_name
from tenant_schemas.signals import post_schema_sync
from tenant_schemas.utils import django_is_in_test_mode, schema_exists
from tenant_schemas.utils import get_public_schema_name


class TenantMixin(models.Model):
    auto_drop_schema = False   # USE THIS WITH CAUTION!
                               # set this flag to true on a parent class if
                               # you want the schema to be automatically
                               # removed after tenant remove.

    auto_create_schema = True  # set this flag to false on a parent class if
                               # you don't want the schema to be automatically
                               # created upon save.

    domain_url = models.CharField(max_length=128, unique=True)
    schema_name = models.CharField(max_length=63, unique=True, validators=[_check_schema_name])

    class Meta:
        abstract = True

    def save(self, verbosity=1, *args, **kwargs):
        is_new = self.pk is None

        if is_new and connection.schema_name != get_public_schema_name():
            raise Exception("Can't create tenant outside the public schema. Current schema is %s."
                            % connection.schema_name)
        elif not is_new and connection.schema_name not in (self.schema_name, get_public_schema_name()):
            raise Exception("Can't update tenant outside it's own schema or the public schema. Current schema is %s."
                            % connection.schema_name)

        super(TenantMixin, self).save(*args, **kwargs)

        if is_new and self.auto_create_schema:
            self.create_schema(check_if_exists=True, verbosity=verbosity)
            post_schema_sync.send(sender=TenantMixin, tenant=self)

    def delete(self, *args, **kwargs):
        """
        Drops the schema related to the tenant instance. Just drop the schema if the parent
        class model has the attribute auto_drop_schema set to True.
        """
        if connection.schema_name not in (self.schema_name, get_public_schema_name()):
            raise Exception("Can't delete tenant outside it's own schema or the public schema. Current schema is %s."
                            % connection.schema_name)

        if schema_exists(self.schema_name) and self.auto_drop_schema:
            cursor = connection.cursor()
            cursor.execute('DROP SCHEMA %s CASCADE' % self.schema_name)
            transaction.commit_unless_managed()

        super(TenantMixin, self).delete(*args, **kwargs)

    def create_schema(self, check_if_exists=False, sync_schema=True, verbosity=1):
        """
        Creates the schema 'schema_name' for this tenant. Optionally checks if the schema
        already exists before creating it. Returns true if the schema was created, false
        otherwise.
        """

        # safety check
        _check_schema_name(self.schema_name)
        cursor = connection.cursor()

        if check_if_exists and schema_exists(self.schema_name):
            return False

        # create the schema
        cursor.execute('CREATE SCHEMA %s' % self.schema_name)
        transaction.commit_unless_managed()

        if sync_schema:
            # default is faking all migrations and syncing directly to the current models state
            fake_all_migrations = getattr(settings, 'TENANT_CREATION_FAKES_MIGRATIONS', True)

            call_command('sync_schemas',
                         schema_name=self.schema_name,
                         tenant=True,
                         public=False,
                         interactive=False,  # don't ask to create an admin user
                         migrate_all=fake_all_migrations,
                         verbosity=verbosity,
                         )

            # run/fake all migrations
            if 'south' in settings.INSTALLED_APPS and not django_is_in_test_mode():
                call_command('migrate_schemas',
                             fake=fake_all_migrations,
                             schema_name=self.schema_name,
                             verbosity=verbosity)

        connection.set_schema_to_public()
        return True
