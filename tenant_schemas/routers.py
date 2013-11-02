from django.conf import settings


class TenantSyncRouter(object):
    """
    A router to control all database operations on models in
    the myapp application
    """

    def allow_syncdb(self, db, model):
        """
        Make sure the myapp app only appears on the 'other' db
        """
        from django.db import connection
        from tenant_schemas.utils import get_public_schema_name, app_labels

        if connection.get_schema() == get_public_schema_name():
            if model._meta.app_label not in app_labels(settings.SHARED_APPS):
                print model._meta.app_label
                return False
        else:
            if model._meta.app_label not in app_labels(settings.TENANT_APPS):
                return False

        return None