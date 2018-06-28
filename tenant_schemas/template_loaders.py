"""
Adaptations of the cached and filesystem template loader working in a
multi-tenant setting
"""

from django.conf import settings
from django.core.exceptions import (
    ImproperlyConfigured, SuspiciousFileOperation)
from django.db import connection
from django.template import Origin
from django.template.loaders.cached import Loader as BaseCachedLoader
from django.template.loaders.filesystem import (
    Loader as BaseFilesystemLoader)
from django.utils._os import safe_join
from django.utils.encoding import force_text

from tenant_schemas.postgresql_backend.base import FakeTenant


class CachedLoader(BaseCachedLoader):
    """Overide django's cached loader."""

    def cache_key(self, template_name, template_dirs=None, skip=None):
        """Override Django's method, injecting tenant pk when available."""
        dirs_prefix = ''
        skip_prefix = ''

        if skip:
            matching = [
                origin.name
                for origin in skip
                if origin.template_name == template_name
            ]
            if matching:
                skip_prefix = self.generate_hash(matching)

        if template_dirs:
            dirs_prefix = self.generate_hash(template_dirs)

        values = [
            s
            for s in (force_text(template_name), skip_prefix, dirs_prefix)
            if s
        ]

        if hasattr(connection.tenant, "pk"):
            values.insert(0, force_text(connection.tenant.pk))

        return '-'.join(values)


class FilesystemLoader(BaseFilesystemLoader):
    """Overide django's filesystem loader."""

    def get_template_sources(self, template_name, template_dirs=None):
        """Override Django's method, replacing template dirs with setting."""
        if not connection.tenant or isinstance(connection.tenant, FakeTenant):
            return

        if not template_dirs:
            try:
                template_dirs = settings.MULTITENANT_TEMPLATE_DIRS
            except AttributeError:
                raise ImproperlyConfigured(
                    'To use %s.%s you must define the MULTITENANT_TEMPLATE_DIRS' %
                    (__name__, FilesystemLoader.__name__)
                )

        for template_dir in template_dirs:
            try:
                name = safe_join(template_dir, template_name)
                if '%s' in template_dir:
                    name = safe_join(
                        template_dir % connection.tenant.domain_url,
                        template_name
                    )
                else:
                    name = safe_join(
                        template_dir,
                        connection.tenant.domain_url,
                        template_name
                    )
            except SuspiciousFileOperation:
                # The joined path was located outside of this template_dir
                # (it might be inside another one, so this isn't fatal).
                continue

            yield Origin(
                name=name,
                template_name=template_name,
                loader=self,
            )
