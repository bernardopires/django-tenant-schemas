"""
Adaptations of the cached and filesystem template loader working in a
multi-tenant setting
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.template.loaders import cached, filesystem
from ordered_set import OrderedSet
from tenant_schemas.postgresql_backend.base import FakeTenant


class CachedLoader(cached.Loader):
    def cache_key(self, *args, **kwargs):
        key = super(CachedLoader, self).cache_key(*args, **kwargs)

        if not connection.tenant or isinstance(connection.tenant, FakeTenant):
            return key

        return "-".join([connection.tenant.schema_name, key])


class FilesystemLoader(filesystem.Loader):
    def get_dirs(self):
        dirs = OrderedSet(super(FilesystemLoader, self).get_dirs())

        if connection.tenant and not isinstance(connection.tenant, FakeTenant):
            try:
                template_dirs = settings.MULTITENANT_TEMPLATE_DIRS
            except AttributeError:
                raise ImproperlyConfigured(
                    "To use %s.%s you must define the MULTITENANT_TEMPLATE_DIRS"
                    % (__name__, FilesystemLoader.__name__)
                )

            for template_dir in reversed(template_dirs):
                dirs.update(
                    [
                        template_dir % (connection.tenant.domain_url,)
                        if "%s" in template_dir
                        else template_dir,
                    ]
                )

        return [each for each in reversed(dirs)]
