import os

from django.core.exceptions import SuspiciousOperation
from django.utils._os import safe_join

from django.db import connection

from django.core.files.storage import FileSystemStorage
from django.contrib.staticfiles.storage import StaticFilesStorage

__all__ = (
    'TenantStorageMixin',
    'TenantFileSystemStorage',
    'TenantStaticFilesStorage',
)


class TenantStorageMixin(object):
    """
    Mixin that can be combined with other Storage backends to colocate media
    for all tenants in distinct subdirectories.

    Using rewriting rules at the reverse proxy we can determine which content
    gets served up, while any code interactions will account for the multiple
    tenancy of the project.
    """
    @property
    def location(self):
        if connection.tenant:
            return safe_join(settings.TENANT_BASE, connection.tenant.domain_url, 'media')
        else:
            return os.path.abspath(self.base_location)


class TenantFileSystemStorage(TenantStorageMixin, FileSystemStorage):
    """
    Implementation that extends core Django's FileSystemStorage.
    """


class TenantStaticFilesStorage(TenantStorageMixin, StaticFilesStorage):
    """
    Implementation that extends core Django's StaticFilesStorage.
    """
