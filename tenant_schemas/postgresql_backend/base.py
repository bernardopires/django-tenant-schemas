import re
import warnings
from django.conf import settings
from django.utils.importlib import import_module
from django.core.exceptions import ImproperlyConfigured
from django.db.models import get_model
from tenant_schemas.utils import get_public_schema_name, get_models_from_appstring
from tenant_schemas.postgresql_backend.creation import SharedDatabaseCreation

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

        self.creation = SharedDatabaseCreation(self)
        self.set_schema_to_public()

    def set_schema(self, schema_name):
        """
        Main API method to current database schema,
        but it does not actually modify the db connection.
        """
        self.tenant = None
        self.schema_name = schema_name

    def set_tenant(self, tenant):
        """
        Main API method to current database schema,
        but it does not actually modify the db connection.
        """
        self.tenant = tenant
        self.schema_name = tenant.schema_name

    def set_schema_to_public(self):
        """
        Instructs to stay in the common 'public' schema.
        """
        self.tenant = None
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
            raise ImproperlyConfigured("Database schema not set. Did your forget "
                                       "to call set_schema() or set_tenant()?")
        _check_identifier(self.schema_name)
        public_schema_name = get_public_schema_name()
        if self.schema_name == public_schema_name:
            cursor.execute('SET search_path = %s', (public_schema_name,))
        else:
            cursor.execute('SET search_path = %s,%s', (self.schema_name, public_schema_name))

        return cursor

    # We need to make it a property, otherwise it
    # "triggers some setup which tries to load the backend which in turn will fail cause it tries to retrigger that"
    # Basically, we can only construct this list in runtime, after the database backend properly built.
    @property
    def shared_apps_models(self):
        """
        Return the list of shared models generated from the SHARED_APPS setting.
        """
        shared_models = []
        # SHARED_APPS is optional, so INSTALLED_APPS will be used if not available
        for appstr in getattr(settings, 'SHARED_APPS', settings.INSTALLED_APPS):
            # South manipulate INSTALLED_APPS on sycdb, so this will just put those in
            # which South needs right now
            if appstr in settings.INSTALLED_APPS:
                shared_models.extend(get_models_from_appstring(appstr))

        return shared_models

    @property
    def tenant_apps_models(self):
        """
        Return the list of tenant models generated from TENANT_APPS setting.
        """
        tenant_models = []
        # TENANT_APPS is optional, so INSTALLED_APPS will be used if not available
        for appstr in getattr(settings, 'TENANT_APPS', settings.INSTALLED_APPS):
            # check for South
            if appstr in settings.INSTALLED_APPS:
                tenant_models.extend(get_models_from_appstring(appstr))

        return tenant_models

    @property
    def shared_models(self):
        """
        Return the list of models generated from SHARED_MODELS setting.

        SHARED_MODELS is an iterable which members are in a form of 'applabel.Model'
        e.g. 'django.contrib.auth.User' --> User model from django.contrib.auth app
        note. shared_models managed will be bypassed
        """
        shared_models = []
        # SHARED_MODELS is optional, so it will be empty if the setting is not available
        for modelstr in getattr(settings, 'SHARED_MODELS', []):
            # Get the full appstring from the modelstring, basically cut the model from the end.
            model_appstr = ".".join(modelstr.split('.')[:-1])
            # check for South
            if model_appstr in settings.INSTALLED_APPS:
                mod_split = modelstr.split('.')
                shared_models.append(get_model(mod_split[-2], mod_split[-1]))

        return shared_models


DatabaseError = original_backend.DatabaseError
IntegrityError = original_backend.IntegrityError
