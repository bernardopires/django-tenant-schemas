import re
from django.conf import settings
from threading import local
from django.utils.importlib import import_module
from django.core.exceptions import ImproperlyConfigured
from django.db import utils
from tenant_schemas.utils import get_public_schema_name

ORIGINAL_BACKEND = getattr(settings, 'ORIGINAL_BACKEND', 'django.db.backends.postgresql_psycopg2')

original_backend = import_module('.base', ORIGINAL_BACKEND)

# from the postgresql doc
SQL_IDENTIFIER_RE = re.compile('^[_a-zA-Z][_a-zA-Z0-9]{,62}$')


def _check_identifier(identifier):
    if not SQL_IDENTIFIER_RE.match(identifier):
        raise RuntimeError("Invalid string used for the schema name.")


class PGThread(local):
    """
    Indicates if the public schema should be included on the search path.
    When syncing the db for creating the tables, it's useful to exclude
    the public schema so that all tables will be created.

    This is a bad monkey patching resulting from the fact that we can't
    separate public from shared apps right now. issue #1 on github
    """
    include_public_schema = True

    def __init__(self):
        self.set_schema_to_public()

    def set_search_path(self, cursor):
        """
        Actual search_path modification for the cursor. Database will
        search schemata from left to right when looking for the object
        (table, index, sequence, etc.).
        """

        if self.schema_name is None:
            raise ImproperlyConfigured("Database schema not set. Did your forget "
                                       "to call set_schema() or set_tenant()?")

        _check_identifier(self.schema_name)
        try:
            public_schema_name = get_public_schema_name()
            if self.schema_name == public_schema_name:
                cursor.execute('SET search_path = %s' % public_schema_name)
            elif self.include_public_schema:
                cursor.execute('SET search_path = %s,%s', [self.schema_name, public_schema_name])
            else:
                cursor.execute('SET search_path = %s', [self.schema_name])
        except utils.DatabaseError, e:
            raise utils.DatabaseError(e.message)

        return cursor

    def get_schema(self):
        return self.schema_name

    def get_tenant(self):
        return self.tenant

    def set_schema(self, schema_name, include_public=True):
        """
        Main API method to current database schema,
        but it does not actually modify the db connection.
        """
        self.tenant = None
        self.schema_name = schema_name
        self.include_public_schema = include_public

    def set_tenant(self, tenant, include_public=True):
        """
        Main API method to current database schema,
        but it does not actually modify the db connection.
        """
        self.tenant = tenant
        self.schema_name = tenant.schema_name
        self.include_public_schema = include_public

        if self.tenant is not None:
            if self.schema_name != self.tenant.schema_name:
                raise ImproperlyConfigured("Passed schema '%s' does not match tenant's schema '%s'."
                                           % (self.schema_name, self.tenant.schema_name))

    def set_schema_to_public(self):
        """
        Instructs to stay in the common 'public' schema.
        """
        self.tenant = None
        self.schema_name = get_public_schema_name()


class DatabaseWrapper(original_backend.DatabaseWrapper):
    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        self.pg_thread = PGThread()

    def set_tenant(self, tenant, include_public = True):
        self.set_settings_schema(tenant.schema_name)
        self.pg_thread.set_tenant(tenant, include_public)

    def set_schema(self, schema_name, include_public = True):
        self.set_settings_schema(schema_name)
        self.pg_thread.set_schema(schema_name, include_public)

    def set_schema_to_public(self):
        self.set_settings_schema(get_public_schema_name())
        self.pg_thread.set_schema_to_public()

    def set_settings_schema(self, schema_name):
        self.settings_dict['SCHEMA'] = schema_name

    def get_schema(self):
        return self.pg_thread.get_schema()

    def get_tenant(self):
        return self.pg_thread.get_tenant()

    def _cursor(self):
        """
        Here it happens. We hope every Django db operation using PostgreSQL
        must go through this to get the cursor handle. We change the path.
        """
        cursor = super(DatabaseWrapper, self)._cursor()
        cursor = self.pg_thread.set_search_path(cursor)
        return cursor

DatabaseError = original_backend.DatabaseError
IntegrityError = original_backend.IntegrityError
