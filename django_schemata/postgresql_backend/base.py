import os, re

from django.conf import settings
from django.utils.importlib import import_module
from django.core.exceptions import ImproperlyConfigured

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

        # By default the schema is not set
        self.schema_name = None

        # but one can change the default using the environment variable.
        force_domain = os.getenv('DJANGO_SCHEMATA_DOMAIN')
        if force_domain:
            self.schema_name = self._resolve_schema_domain(force_domain)['schema_name']

    def _resolve_schema_domain(self, domain_name):
        try:
            sd = settings.SCHEMATA_DOMAINS[domain_name]
        except KeyError:
            raise ImproperlyConfigured("Domain '%s' is not supported by "
                                       "settings.SCHEMATA_DOMAINS" % domain_name)
        return sd

    def _set_pg_search_path(self, cursor):
        """
        Actual search_path modification for the cursor. Database will
        search schemata from left to right when looking for the object
        (table, index, sequence, etc.).
        """
        if self.schema_name is None:
            if settings.DEBUG:
                full_info = " Choices are: %s." \
                            % ', '.join(settings.SCHEMATA_DOMAINS.keys())
            else:
                full_info = ""
            raise ImproperlyConfigured("Database schema not set (you can pick "
                                       "one of the supported domains by setting "
                                       "then DJANGO_SCHEMATA_DOMAIN environment "
                                       "variable.%s)" % full_info)

        _check_identifier(self.schema_name)
        if self.schema_name == 'public':
            cursor.execute('SET search_path = public')
        else:
            cursor.execute('SET search_path = %s, public', [self.schema_name])

    def set_schemata_domain(self, domain_name):
        """
        Main API method to current database schema,
        but it does not actually modify the db connection.
        Returns the particular domain dict from settings.SCHEMATA_DOMAINS. 
        """
        sd = self._resolve_schema_domain(domain_name)
        self.schema_name = sd['schema_name']
        return sd

    def set_schemata_off(self):
        """
        Instructs to stay in the common 'public' schema.
        """
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
