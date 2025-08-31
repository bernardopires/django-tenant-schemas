from django.conf import settings
from django.db import connection
from django.db.utils import load_backend

from tenant_schemas.postgresql_backend.base import DatabaseWrapper as TenantDbWrapper
from tenant_schemas.utils import app_labels, get_public_schema_name


class TenantSyncRouter(object):
    """
    A router to control which applications will be synced,
    depending if we are syncing the shared apps or the tenant apps.
    """

    def allow_migrate(self, db, app_label, model_name=None, **hints):

        db_engine = settings.DATABASES[db]['ENGINE']
        if not (db_engine == 'tenant_schemas.postgresql_backend' or
                issubclass(getattr(load_backend(db_engine), 'DatabaseWrapper'), TenantDbWrapper)):
            return None


        if connection.schema_name == get_public_schema_name():
            if app_label not in app_labels(settings.SHARED_APPS):
                return False
        else:
            if app_label not in app_labels(settings.TENANT_APPS):
                return False

        return None

