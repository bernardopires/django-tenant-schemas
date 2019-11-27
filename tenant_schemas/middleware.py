import django
from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.db import connection
from django.http import Http404
from tenant_schemas.utils import (
    get_public_schema_name,
    get_tenant_model,
    remove_www,
)


"""
These middlewares should be placed at the very top of the middleware stack.
Selects the proper database schema using request information. Can fail in
various ways which is better than corrupting or revealing data.

Extend BaseTenantMiddleware for a custom tenant selection strategy,
such as inspecting the header, or extracting it from some OAuth token.
"""


class BaseTenantMiddleware(django.utils.deprecation.MiddlewareMixin):
    TENANT_NOT_FOUND_EXCEPTION = Http404

    """
    Subclass and override  this to achieve desired behaviour. Given a
    request, return the tenant to use. Tenant should be an instance
    of TENANT_MODEL. We have three parameters for backwards compatibility
    (the request would be enough).
    """

    def get_tenant(self, model, hostname, request):
        raise NotImplementedError

    def hostname_from_request(self, request):
        """ Extracts hostname from request. Used for custom requests filtering.
            By default removes the request's port and common prefixes.
        """
        return remove_www(request.get_host().split(":")[0]).lower()

    def process_request(self, request):
        # Connection needs first to be at the public schema, as this is where
        # the tenant metadata is stored.
        connection.set_schema_to_public()

        hostname = self.hostname_from_request(request)
        TenantModel = get_tenant_model()

        try:
            # get_tenant must be implemented by extending this class.
            tenant = self.get_tenant(TenantModel, hostname, request)
            assert isinstance(tenant, TenantModel)
        except TenantModel.DoesNotExist:
            raise self.TENANT_NOT_FOUND_EXCEPTION(
                "No tenant for {!r}".format(request.get_host())
            )
        except AssertionError:
            raise self.TENANT_NOT_FOUND_EXCEPTION(
                "Invalid tenant {!r}".format(request.tenant)
            )

        request.tenant = tenant
        connection.set_tenant(request.tenant)

        # Do we have a public-specific urlconf?
        if (
            hasattr(settings, "PUBLIC_SCHEMA_URLCONF")
            and request.tenant.schema_name == get_public_schema_name()
        ):
            request.urlconf = settings.PUBLIC_SCHEMA_URLCONF


class TenantMiddleware(BaseTenantMiddleware):
    """
    Selects the proper database schema using the request host. E.g. <my_tenant>.<my_domain>
    """

    def get_tenant(self, model, hostname, request):
        return model.objects.get(domain_url=hostname)


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
                model, hostname, request
            )
        except model.DoesNotExist:
            schema_name = self.DEFAULT_SCHEMA_NAME
            if not schema_name:
                schema_name = get_public_schema_name()

            return model.objects.get(schema_name=schema_name)
