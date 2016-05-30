from django.conf import settings
from django.db.models.base import ModelBase


class TenantSyncRouter(object):
    """
    A router to control which applications will be synced,
    depending if we are syncing the shared apps or the tenant apps.
    """

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # the imports below need to be done here else django <1.5 goes crazy
        # https://code.djangoproject.com/ticket/20704
        from django.db import connection
        from tenant_schemas.utils import get_public_schema_name, app_labels

        if isinstance(app_label, ModelBase):
            # In django <1.7 the `app_label` parameter is actually `model`
            app_label = app_label._meta.app_label

        if connection.schema_name == get_public_schema_name():
            if app_label not in app_labels(settings.SHARED_APPS):
                return False
        else:
            if app_label not in app_labels(settings.TENANT_APPS):
                return False

        return None

    def allow_syncdb(self, db, model):
        # allow_syncdb was changed to allow_migrate in django 1.7
        return self.allow_migrate(db, model)
