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
        # connection needs first to be at the public schema, as this is where the
        # tenant informations are saved
        connection.set_schema_to_public()
        hostname_without_port = remove_www_and_dev(request.get_host().split(':')[0])

        request.tenant = get_object_or_404(get_tenant_model(), domain_url=hostname_without_port)
        connection.set_tenant(request.tenant)

        # content type can no longer be cached as public and tenant schemas have different
        # models. if someone wants to change this, the cache needs to be separated between
        # public and shared schemas. if this cache isn't cleared, this can cause permission
        # problems. for example, on public, a particular model has id 14, but on the tenants
        # it has the id 15. if 14 is cached instead of 15, the permissions for the wrong
        # model will be fetched.
        ContentType.objects.clear_cache()

        # do we have a public-specific token?
        if hasattr(settings, 'PUBLIC_SCHEMA_URLCONF') and request.tenant.schema_name == get_public_schema_name():
            request.urlconf = settings.PUBLIC_SCHEMA_URLCONF
