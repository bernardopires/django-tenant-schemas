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
    """
    Adds the capability to manipulate the search_path using set_tenant and set_schema_name
    """
    include_public_schema = True

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        self.creation = SharedDatabaseCreation(self)
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
        self.tenant = None
        self.schema_name = schema_name
        self.include_public_schema = include_public

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
            cursor.execute('SET search_path = %s' % public_schema_name)
        elif self.include_public_schema:
            cursor.execute('SET search_path = %s,%s', [self.schema_name, public_schema_name])
        else:
            cursor.execute('SET search_path = %s', [self.schema_name])

        return cursor

    # We need to make it a property, otherwise it
    # "triggers some setup which tries to load the backend which in turn will fail cause it tries to retrigger that"
    # Basically, we can only construct this list in runtime, after the database backend properly built.
    @property
    def shared_models(self):
        """Return the list of public models.

        It is generated from the setting SHARED_APPS and SHARED_MODELS.
        The results are cached in _shared_models attribute.
        SHARED_MODELS is an iterable which members are in a form of 'applabel.Model'.
        """
        self._shared_models = []

        shared_apps = getattr(settings, 'SHARED_APPS') if hasattr(settings, 'SHARED_APPS') else settings.INSTALLED_APPS

        for app in shared_apps:
            if app in settings.INSTALLED_APPS:
                self._shared_models.extend(get_models_from_appstring(app))

        # append the list of models generated from SHARED_MODELS setting
        for modelstring in getattr(settings, 'SHARED_MODELS'):
            model = get_model(*modelstring.split('.'))
            if model and model not in self._shared_models and model._meta.app_label in settings.INSTALLED_APPS:
                self._shared_models.append(model)

        return self._shared_models

    @property
    def tenant_models(self):
        """Return the list of tenant models generated from the setting TENANT_APPS.

        But only those which are not in SHARED_MODELS.
        If a model is either in SHARED_APPS and TENANT_APPS, it will be included here.
        """
        self._tenant_models = []
        tenant_apps = getattr(settings, 'TENANT_APPS') if hasattr(settings, 'TENANT_APPS') else settings.INSTALLED_APPS
        shared_models = [get_model(*app.split('.')) for app in getattr(settings, 'SHARED_MODELS', None)]

        for app in tenant_apps:
            if app not in settings.INSTALLED_APPS:
                continue
            app_models = get_models_from_appstring(app)
            # remove models which are in SHARED_MODELS setting, so those will be forced to public
            models = filter(lambda mod: mod not in shared_models, app_models)
            self._tenant_models.extend(models)

        return self._tenant_models


DatabaseError = original_backend.DatabaseError
IntegrityError = original_backend.IntegrityError
