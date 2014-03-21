import re
import warnings
from django.conf import settings
from django.utils.importlib import import_module
from django.core.exceptions import ImproperlyConfigured
from tenant_schemas.utils import get_public_schema_name

ORIGINAL_BACKEND = getattr(settings, 'ORIGINAL_BACKEND', 'django.db.backends.postgresql_psycopg2')

original_backend = import_module('.base', ORIGINAL_BACKEND)

EXTRA_SEARCH_PATHS = getattr(settings, 'PG_EXTRA_SEARCH_PATHS', [])

# from the postgresql doc
SQL_IDENTIFIER_RE = re.compile('^[_a-zA-Z][_a-zA-Z0-9]{,62}$')


def _check_identifier(identifier):
    if not SQL_IDENTIFIER_RE.match(identifier):
        raise RuntimeError("Invalid string used for the schema name.")


class DatabaseWrapper(original_backend.DatabaseWrapper):
    """
    Adds the capability to manipulate the search_path using set_tenant and set_schema_name
    """
    include_public_schema = True

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self.set_schema_to_public()

    def set_tenant(self, tenant, include_public=True):
        """
        Main API method to current database schema,
        but it does not actually modify the db connection.
        """
        self.tenant = tenant
        self.schema_name = tenant.schema_name
        self.include_public_schema = include_public

    def set_schema(self, schema_name, include_public=True):
        """
        Main API method to current database schema,
        but it does not actually modify the db connection.
        """
        self.tenant = FakeTenant(schema_name=schema_name)
        self.schema_name = schema_name
        self.include_public_schema = include_public

    def set_schema_to_public(self):
        """
        Instructs to stay in the common 'public' schema.
        """
        self.tenant = FakeTenant(schema_name=get_public_schema_name())
        self.schema_name = get_public_schema_name()

    def get_schema(self):
        warnings.warn("connection.get_schema() is deprecated, use connection.schema_name instead.",
                      category=DeprecationWarning)
        return self.schema_name

    def get_tenant(self):
        warnings.warn("connection.get_tenant() is deprecated, use connection.tenant instead.",
                      category=DeprecationWarning)
        return self.tenant

    def _cursor(self):
        """
        Here it happens. We hope every Django db operation using PostgreSQL
        must go through this to get the cursor handle. We change the path.
        """
        cursor = super(DatabaseWrapper, self)._cursor()

        # Actual search_path modification for the cursor. Database will
        # search schemata from left to right when looking for the object
        # (table, index, sequence, etc.).
        if not self.schema_name:
            raise ImproperlyConfigured("Database schema not set. Did you forget "
                                       "to call set_schema() or set_tenant()?")
        _check_identifier(self.schema_name)
        public_schema_name = get_public_schema_name()
        search_paths = []

        if self.schema_name == public_schema_name:
            search_paths = [public_schema_name]
        elif self.include_public_schema:
            search_paths = [self.schema_name, public_schema_name]
        else:
            search_paths = [self.schema_name]

        search_paths.extend(EXTRA_SEARCH_PATHS)
        cursor.execute('SET search_path = {}'.format(','.join(search_paths)))
        return cursor


class FakeTenant:
    """
    We can't import any db model in a backend (apparently?), so this class is used
    for wrapping schema names in a tenant-like structure.
    """
    def __init__(self, schema_name):
        self.schema_name = schema_name

DatabaseError = original_backend.DatabaseError
IntegrityError = original_backend.IntegrityError
