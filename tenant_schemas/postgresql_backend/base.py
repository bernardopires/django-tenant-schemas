import os, re

from django.conf import settings
from django.utils.importlib import import_module
from django.core.exceptions import ImproperlyConfigured
from tenant_schemas.utils import get_tenant_model

ORIGINAL_BACKEND = getattr(settings, 'ORIGINAL_BACKEND', 'django.db.backends.postgresql_psycopg2')

original_backend = import_module('.base', ORIGINAL_BACKEND)

# from the postgresql doc
SQL_IDENTIFIER_RE = re.compile('^[_a-zA-Z][_a-zA-Z0-9]{,62}$')

def _check_identifier(identifier):
    if not SQL_IDENTIFIER_RE.match(identifier):
        raise RuntimeError("Invalid string used for the schema name.")

class DatabaseWrapper(original_backend.DatabaseWrapper):
    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        # By default the schema is public
        self.set_schema_to_public()

    def _set_pg_search_path(self, cursor):
        """
        Actual search_path modification for the cursor. Database will
        search schemata from left to right when looking for the object
        (table, index, sequence, etc.).
        """
        if self.schema_name is None:
            raise ImproperlyConfigured("Database schema not set. Did your forget "
                                       "to call set_schema() or set_tenant()?")

        _check_identifier(self.schema_name)
        if self.schema_name == 'public':
            cursor.execute('SET search_path = public')
        else:
            cursor.execute('SET search_path = %s, public', [self.schema_name])

    def set_schema(self, schema_name):
        """
        Main API method to current database schema,
        but it does not actually modify the db connection.
        """
        self.schema_name = schema_name

    def set_tenant(self, tenant):
        """
        Main API method to current database schema,
        but it does not actually modify the db connection.
        """
        self.tenant = tenant
        self.schema_name = tenant.schema_name

        if self.tenant is not None:
            if self.schema_name != self.tenant.schema_name:
                raise ImproperlyConfigured("Passed schema '%s' does not match tenant's schema '%s'."
                % (self.schema_name, self.tenant.schema_name))

    def set_schema_to_public(self):
        """
        Instructs to stay in the common 'public' schema.
        """
        self.tenant = None
        self.schema_name = 'public'

    def _cursor(self):
        """
        Here it happens. We hope every Django db operation using PostgreSQL
        must go through this to get the cursor handle. We change the path.
        """ 
        cursor = super(DatabaseWrapper, self)._cursor()
        self._set_pg_search_path(cursor)
        return cursor

DatabaseError = original_backend.DatabaseError
IntegrityError = original_backend.IntegrityError
