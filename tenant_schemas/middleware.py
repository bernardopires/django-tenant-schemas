import django

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import DisallowedHost
from django.db import connection
from django.http import Http404
from tenant_schemas.utils import (get_tenant_model, remove_www,
                                  get_public_schema_name)

if django.VERSION >= (1, 10, 0):
    MIDDLEWARE_MIXIN = django.utils.deprecation.MiddlewareMixin
else:
    MIDDLEWARE_MIXIN = object


class TenantMiddleware(MIDDLEWARE_MIXIN):
    """
    This middleware should be placed at the very top of the middleware stack.
    Selects the proper database schema using the request host. Can fail in
    various ways which is better than corrupting or revealing data.
    """
    TENANT_NOT_FOUND_EXCEPTION = Http404

    def hostname_from_request(self, request):
        """ Extracts hostname from request. Used for custom requests filtering.
            By default removes the request's port and common prefixes.
        """
        return remove_www(request.get_host().split(':')[0]).lower()

    def get_tenant(self, model, hostname, request):
        return model.objects.get(domain_url=hostname)

    def process_request(self, request):
        # Connection needs first to be at the public schema, as this is where
        # the tenant metadata is stored.
        connection.set_schema_to_public()
        hostname = self.hostname_from_request(request)

        TenantModel = get_tenant_model()

        try:
            request.tenant = self.get_tenant(TenantModel, hostname, request)
            connection.set_tenant(request.tenant)
        except TenantModel.DoesNotExist:
            raise self.TENANT_NOT_FOUND_EXCEPTION(
                'No tenant for hostname "%s"' % hostname)

        # Content type can no longer be cached as public and tenant schemas
        # have different models. If someone wants to change this, the cache
        # needs to be separated between public and shared schemas. If this
        # cache isn't cleared, this can cause permission problems. For example,
        # on public, a particular model has id 14, but on the tenants it has
        # the id 15. if 14 is cached instead of 15, the permissions for the
        # wrong model will be fetched.
        ContentType.objects.clear_cache()

        # Do we have a public-specific urlconf?
        if hasattr(settings, 'PUBLIC_SCHEMA_URLCONF') and request.tenant.schema_name == get_public_schema_name():
            request.urlconf = settings.PUBLIC_SCHEMA_URLCONF


class SuspiciousTenantMiddleware(TenantMiddleware):
    """
    Extend the TenantMiddleware in scenario where you need to configure
    ``ALLOWED_HOSTS`` to allow ANY domain_url to be used because your tenants
    can bring any custom domain with them, as opposed to all tenants being a
    subdomain of a common base.

    See https://github.com/bernardopires/django-tenant-schemas/pull/269 for
    discussion on this middleware.
    """
    TENANT_NOT_FOUND_EXCEPTION = DisallowedHost


class DefaultTenantMiddleware(SuspiciousTenantMiddleware):
    """
    Extend the SuspiciousTenantMiddleware in scenario where you want to
    configure a tenant to be served if the hostname does not match any of the
    existing tenants.

    Subclass and override DEFAULT_SCHEMA_NAME to use a schema other than the
    public schema.

        class MyTenantMiddleware(DefaultTenantMiddleware):
            DEFAULT_SCHEMA_NAME = 'default'
    """
    DEFAULT_SCHEMA_NAME = None

    def get_tenant(self, model, hostname, request):
        try:
            return super(DefaultTenantMiddleware, self).get_tenant(
                model, hostname, request)
        except model.DoesNotExist:
            schema_name = self.DEFAULT_SCHEMA_NAME
            if not schema_name:
                schema_name = get_public_schema_name()

            return model.objects.get(schema_name=schema_name)
