from abc import ABCMeta, abstractmethod

from django.db import connection

from tenant_schemas.utils import get_tenant_model, get_public_schema_name, remove_www_and_dev

class TenantNotFound(RuntimeError):
    pass

class TenantAdapterIface(object):
    """Interface for retrieving tenants:
       - sync_schemas and migrate_schemas comands need to list tenants, so there is a
         get_tenants() method,
       - TenantMiddleware need to find a tenant given a request, so there is a
         get_tenant_for_request() method,
       - sync_schemas, migrate_schemas and tenant_command command need to get a
         tenant by name so there is get_tenant_by_name() method.

       The only interface for the returned tenant is that it must have a
       property named 'schema_name'.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_tenants(self):
        return []

    @abstractmethod
    def get_tenant_for_request(self, request):
        '''Retrieve a tenant for this request, if none is found KeyError is raised'''
        return None

    @abstractmethod
    def get_tenant_by_name(self, schema_name):
        return None

class ModelTenantAdapter(TenantAdapterIface):
    """Classical tenant stored in models of the public schema"""

    def get_tenants(self):
        connection.set_schema_to_public()
        return get_tenant_model().objects.all()

    def hostname_from_request(self, request):
        """ Extracts hostname from request. Used for custom requests filtering.
            By default removes the request's port and common prefixes.
        """
        return remove_www_and_dev(request.get_host().split(':')[0])

    def get_tenant_for_request(self, request):
        connection.set_schema_to_public()
        hostname = self.hostname_from_request(request)
        model = get_tenant_model()
        try:
            return model.objects.get(domain_url=hostname)
        except model.DoesNotExist:
            raise TenantNotFound('no tenant found for domain %s' % hostname)

    def get_tenant_by_name(self, schema_name):
        connection.set_schema_to_public()
        model = get_tenant_model()
        try:
            return model.objects.get(schema_name=schema_name)
        except model.DoesNotExist:
            raise TenantNotFound('no tenant found with schema name %s' % schema_name)
