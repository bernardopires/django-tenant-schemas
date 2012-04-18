import os, re

from django.conf import settings
from django.utils.importlib import import_module
from django.core.exceptions import ImproperlyConfigured

ORIGINAL_BACKEND = getattr(settings, 'ORIGINAL_BACKEND', 'django.db.backends.oracle')

original_backend = import_module('.base', ORIGINAL_BACKEND)

SQL_IDENTIFIER_RE = re.compile('^[_a-zA-Z][_a-zA-Z0-9]{,30}$')

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
        except KeyError, er:
            print er
            raise ImproperlyConfigured("Domain '%s' is not supported by "
                                       "settings.SCHEMATA_DOMAINS" % domain_name)
        return sd

    def _set_oracle_default_schema(self, cursor):
        '''
        this is somewhat the equivalent of postgresql_backend ``_set_pg_search_path``

        .. note::

            ORACLE does not allow a fallback to the current USER schema like in
            PostgreSQL with the ``public`` schema
        '''
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

        base_sql_command = 'ALTER SESSION SET current_schema = '

        if self.schema_name == '':
            # set the current_schema to a current USER
            cursor.execute("""begin
                    EXECUTE IMMEDIATE '%s' || USER; 
                    end;
                    /""" % base_sql_command)
        else:
            _check_identifier(self.schema_name)
            sql_command = base_sql_command + self.schema_name
            cursor.execute(sql_command)

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
        self.schema_name = ''

    def _cursor(self):
        """
        Here it happens. We hope every Django db operation using Oracle
        must go through this to get the cursor handle.
        """ 
        cursor = super(DatabaseWrapper, self)._cursor()
        self._set_oracle_default_schema(cursor)
        return cursor

DatabaseError = original_backend.DatabaseError
IntegrityError = original_backend.IntegrityError
