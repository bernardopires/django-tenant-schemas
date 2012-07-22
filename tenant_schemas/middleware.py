from django.conf import settings
from django.db import connection
from django.shortcuts import get_object_or_404
from tenant_schemas.utils import get_tenant_model, remove_www_and_dev

class TenantMiddleware(object):
    """
    This middleware should be placed at the very top of the middleware stack.
    Selects the proper database schema using the request host. Can fail in
    various ways which is better than corrupting or revealing data...

    If the request comes from a subdomain (a schema that isn't public), a token is added to the request URL
    path to force django to route this to schema-dependent views. This allows different views at the same URL.

    This schema-token is removed automatically when calling the schemata url tag or the reverse function.
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

        # do we have tenant-specific URLs?
        if settings.PUBLIC_SCHEMA_URL_TOKEN and request.tenant.schema_name == "public" and request.path_info[-1] == '/':
            # we are not at the public schema, manually alter routing to schema-dependent urls
            request.path_info = settings.PUBLIC_SCHEMA_URL_TOKEN + request.path_info