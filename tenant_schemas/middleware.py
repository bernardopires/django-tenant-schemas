# coding:utf-8

"""
    Dynamic Site pieces borrowed from https://github.com/jedie which assembled them from multiple snippets
"""

import os
from django.conf import settings
from django.db import connection
from django.shortcuts import get_object_or_404
from tenant_schemas.utils import get_tenant_model, remove_www_and_dev, get_public_schema_name

try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local


class DynamicTenantSiteId(object):
    def __getattribute__(self, name):
        return getattr(SITE_THREAD_LOCAL.SITE_ID, name)

    def __int__(self):
        return SITE_THREAD_LOCAL.SITE_ID

    def __hash__(self):
        return hash(SITE_THREAD_LOCAL.SITE_ID)

    def __repr__(self):
        return repr(SITE_THREAD_LOCAL.SITE_ID)

    def __str__(self):
        return str(SITE_THREAD_LOCAL.SITE_ID)

    def __unicode__(self):
        return unicode(SITE_THREAD_LOCAL.SITE_ID)

SET_TENANT_SITE_DYNAMICALLY = getattr(settings, "TENANT_DYNAMIC_SITE", False)

if SET_TENANT_SITE_DYNAMICALLY:
    DEFAULT_SITE_ID = int(getattr(os.environ, "SITE_ID", settings.SITE_ID))
    SITE_THREAD_LOCAL = local()
    settings.SITE_ID = DynamicTenantSiteId()


class TenantMiddleware(object):
    """
    This middleware should be placed at the very top of the middleware stack.
    Selects the proper database schema using the request host. Can fail in
    various ways which is better than corrupting or revealing data...

    If the request comes from a subdomain (a schema that isn't public), a token is added to the request URL
    path to force django to route this to schema-dependent views. This allows different views at the same URL.

    This schema-token is removed automatically when calling the schemata url tag or the reverse function.
    """

    def __init__(self):
        self.TenantModel = get_tenant_model()
        super(TenantMiddleware, self).__init__()

    def process_request(self, request):
        """
        Resets to public schema

        Some nasty weird bugs happened at the production environment without this call.
        connection.pg_thread.schema_name would already be set and then terrible errors
        would occur. Any idea why? My theory is django implements connection as some sort
        of threading local variable.
        """
        connection.set_schema_to_public()
        request.tenant = self.set_tenant(request.get_host())

        # do we have tenant-specific URLs?
        if hasattr(settings, 'PUBLIC_SCHEMA_URL_TOKEN') and request.tenant.schema_name == get_public_schema_name() and request.path_info[-1] == '/':
            # we are not at the public schema, manually alter routing to schema-dependent urls
            request.path_info = settings.PUBLIC_SCHEMA_URL_TOKEN + request.path_info

        if SET_TENANT_SITE_DYNAMICALLY and hasattr(request.tenant, 'site') and request.tenant.site:
            SITE_THREAD_LOCAL.SITE_ID = request.tenant.site_id
            #dynamically set the site

    def set_tenant(self, host):
        tenant = self.get_tenant(host)
        connection.set_tenant(tenant)
        return tenant

    def get_tenant(self, host):
        hostname_without_port = remove_www_and_dev(host.split(':')[0])
        return get_object_or_404(self.TenantModel, domain_url=hostname_without_port)
