from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.shortcuts import get_object_or_404
from tenant_schemas.utils import get_tenant_model, remove_www_and_dev, get_public_schema_name


class TenantMiddleware(object):
    """
    This middleware should be placed at the very top of the middleware stack.
    Selects the proper database schema using the request host. Can fail in
    various ways which is better than corrupting or revealing data...
    """
    def process_request(self, request):
        """
        Resets to public schema

        Some nasty weird bugs happened at the production environment without this call.
        connection.pg_thread.schema_name would already be set and then terrible errors
        would occur. Any idea why? My theory is django implements connection as some sort
        of threading local variable.
        """
        connection.set_schema_to_public()
        hostname_without_port = remove_www_and_dev(request.get_host().split(':')[0])

        TenantModel = get_tenant_model()
        request.tenant = get_object_or_404(TenantModel, domain_url=hostname_without_port)
        connection.set_tenant(request.tenant)

        # content type can no longer be cached as public and tenant schemas have different
        # models. if someone wants to change this, the cache needs to be separated between
        # public and shared schemas. if this cache isn't cleared, this can cause permission
        # problems. for example, on public, a particular model has id 14, but on the tenants
        # it has the id 15. if 14 is cached instead of 15, the permissions for the wrong
        # model will be fetched.
        ContentType.objects.clear_cache()

        # do we have a public-specific token?
        if hasattr(settings, 'PUBLIC_SCHEMA_URL_TOKEN') and request.tenant.schema_name == get_public_schema_name():
            request.path_info = settings.PUBLIC_SCHEMA_URL_TOKEN + request.path_info
