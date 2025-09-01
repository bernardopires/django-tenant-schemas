import re
import warnings
from contextvars import ContextVar

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured, ValidationError
import django.db.utils

from tenant_schemas.utils import get_public_schema_name, get_limit_set_calls
from tenant_schemas.postgresql_backend.introspection import DatabaseSchemaIntrospection

try:
    try:
        from psycopg import InternalError
    except ImportError:
        from psycopg2 import InternalError
except ImportError:
    raise ImproperlyConfigured("Error loading psycopg2 or psycopg module")


ORIGINAL_BACKEND = getattr(
    settings, "ORIGINAL_BACKEND", "django.db.backends.postgresql"
)
original_backend = django.db.utils.load_backend(ORIGINAL_BACKEND)

EXTRA_SEARCH_PATHS = getattr(settings, "PG_EXTRA_SEARCH_PATHS", [])

# ContextVar to prevent recursion when setting search_path under DEBUG=True with psycopg3
_SETTING_SEARCH_PATH = ContextVar("ts_setting_search_path", default=False)

# from the postgresql doc
SQL_IDENTIFIER_RE = re.compile(r"^[_a-zA-Z][_a-zA-Z0-9]{,62}$")
SQL_SCHEMA_NAME_RESERVED_RE = re.compile(r"^pg_", re.IGNORECASE)


def _is_valid_identifier(identifier):
    return bool(SQL_IDENTIFIER_RE.match(identifier))


def _check_identifier(identifier):
    if not _is_valid_identifier(identifier):
        raise ValidationError("Invalid string used for the identifier.")


def _is_valid_schema_name(name):
    return _is_valid_identifier(name) and not SQL_SCHEMA_NAME_RESERVED_RE.match(name)


def _check_schema_name(name):
    if not _is_valid_schema_name(name):
        raise ValidationError("Invalid string used for the schema name.")


class DatabaseWrapper(original_backend.DatabaseWrapper):
    """
    Adds the capability to manipulate the search_path using set_tenant and set_schema_name
    """

    include_public_schema = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Use a patched version of the DatabaseIntrospection that only returns the table list for the
        # currently selected schema.
        self.introspection = DatabaseSchemaIntrospection(self)
        self._ts_last_path_sig = None  # Cache for last applied search path signature
        self.set_schema_to_public()

    def close(self):
        self.search_path_set = False
        self._ts_last_path_sig = None  # Clear cache on close
        super().close()

    def rollback(self):
        super().rollback()
        # Django's rollback clears the search path so we have to set it again the next time.
        self.search_path_set = False
        self._ts_last_path_sig = None  # Clear cache on rollback

    def set_tenant(self, tenant, include_public=True):
        """
        Main API method to current database schema,
        but it does not actually modify the db connection.
        """
        self.set_schema(tenant.schema_name, include_public)
        self.tenant = tenant

    def set_schema(self, schema_name, include_public=True):
        """
        Main API method to current database schema,
        but it does not actually modify the db connection.
        """
        self.tenant = FakeTenant(schema_name=schema_name)
        self.schema_name = schema_name
        self.include_public_schema = include_public
        self.set_settings_schema(schema_name)
        self.search_path_set = False
        self._ts_last_path_sig = None  # Clear cache when schema changes
        # Content type can no longer be cached as public and tenant schemas
        # have different models. If someone wants to change this, the cache
        # needs to be separated between public and shared schemas. If this
        # cache isn't cleared, this can cause permission problems. For example,
        # on public, a particular model has id 14, but on the tenants it has
        # the id 15. if 14 is cached instead of 15, the permissions for the
        # wrong model will be fetched.
        ContentType.objects.clear_cache()

    def set_schema_to_public(self):
        """
        Instructs to stay in the common 'public' schema.
        """
        self.set_schema(get_public_schema_name())

    def set_settings_schema(self, schema_name):
        self.settings_dict["SCHEMA"] = schema_name

    def get_schema(self):
        warnings.warn(
            "connection.get_schema() is deprecated, use connection.schema_name instead.",
            category=DeprecationWarning,
        )
        return self.schema_name

    def get_tenant(self):
        warnings.warn(
            "connection.get_tenant() is deprecated, use connection.tenant instead.",
            category=DeprecationWarning,
        )
        return self.tenant

    def _cursor(self, name=None):
        """
        Here it happens. We hope every Django db operation using PostgreSQL
        must go through this to get the cursor handle. We change the path.
        """
        if name:
            # Create server-side cursor (supported across Django versions)
            cursor = super()._cursor(name=name)
        else:
            cursor = super()._cursor()

        # Calculate search paths for current tenant configuration
        if not self.schema_name:
            raise ImproperlyConfigured(
                "Database schema not set. Did you forget "
                "to call set_schema() or set_tenant()?"
            )

        _check_schema_name(self.schema_name)
        public_schema_name = get_public_schema_name()
        search_paths = []

        if self.schema_name == public_schema_name:
            search_paths = [public_schema_name]
        elif self.include_public_schema:
            search_paths = [self.schema_name, public_schema_name]
        else:
            search_paths = [self.schema_name]

        search_paths.extend(EXTRA_SEARCH_PATHS)
        path_sig = tuple(search_paths)

        # Check if we need to set the search path
        should_set_path = (
            not get_limit_set_calls() or not self.search_path_set
        ) and self._ts_last_path_sig != path_sig

        if should_set_path:
            # Prevent recursion during debug/mogrify operations with psycopg3
            if _SETTING_SEARCH_PATH.get():
                return cursor

            token = _SETTING_SEARCH_PATH.set(True)
            try:
                if name:
                    # Named cursor can only be used once
                    cursor_for_search_path = self.connection.cursor()
                else:
                    # Reuse - get raw cursor to avoid Django's debug wrapper
                    cursor_for_search_path = cursor
                    # For psycopg3 compatibility, get the raw DB-API cursor
                    raw_cursor = getattr(
                        cursor_for_search_path, "cursor", cursor_for_search_path
                    )

                # In the event that an error already happened in this transaction and we are going
                # to rollback we should just ignore database error when setting the search_path
                # if the next instruction is not a rollback it will just fail also, so
                # we do not have to worry that it's not the good one
                try:
                    # Use set_config with parameters instead of raw SQL formatting to avoid
                    # triggering Django's debug SQL logging that causes psycopg3 recursion
                    if name:
                        cursor_for_search_path.execute(
                            "SELECT set_config('search_path', %s, false)",
                            [",".join(search_paths)],
                        )
                    else:
                        raw_cursor.execute(
                            "SELECT set_config('search_path', %s, false)",
                            [",".join(search_paths)],
                        )
                except (django.db.utils.DatabaseError, InternalError):
                    self.search_path_set = False
                    self._ts_last_path_sig = None
                else:
                    self.search_path_set = True
                    self._ts_last_path_sig = path_sig

                if name:
                    cursor_for_search_path.close()
            finally:
                _SETTING_SEARCH_PATH.reset(token)

        return cursor

    def last_executed_query(self, cursor, sql, params):
        """
        Override to avoid opening a fresh cursor during mogrify when there are no params.
        This helps prevent recursion issues with psycopg3 when DEBUG=True.
        """
        if not params:  # no need to mogrify, avoids opening a fresh cursor
            return sql
        # Delegate to the operations class
        return self.ops.last_executed_query(cursor, sql, params)


class FakeTenant:
    """
    We can't import any db model in a backend (apparently?), so this class is used
    for wrapping schema names in a tenant-like structure.
    """

    def __init__(self, schema_name):
        self.schema_name = schema_name
