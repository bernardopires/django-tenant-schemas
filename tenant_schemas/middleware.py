from django.conf import settings
from django.db import connection
from django.db.models.loading import get_model
from django.shortcuts import get_object_or_404
from tenant_schemas.utils import get_tenant_model

class SchemataMiddleware(object):
    """
    This middleware should be placed at the very top of the middleware stack.
    Selects the proper database schema using the request host. Can fail in
    various ways which is better than corrupting or revealing data...

    If the request comes from a subdomain (a schema that isn't public), a token is added to the request URL
    path to force django to route this to schema-dependent views. This allows different views at the same URL.

    This schema-token is removed automatically when calling the schemata url tag or the reverse function.
    """
    def process_request(self, request):
        hostname_without_port = request.get_host().split(':')[0]

        tenant_model = get_tenant_model()
        request.tenant = get_object_or_404(tenant_model, domain_url=hostname_without_port)
        connection.set_tenant(request.tenant)

        if request.tenant.schema_name != "public" and request.path_info[-1] == '/':
            # we are not at the public schema, manually alter routing to schema-dependent urls
            request.path_info = settings.TENANT_URL_TOKEN + request.path_info