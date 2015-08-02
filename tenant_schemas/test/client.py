from django.test import RequestFactory, Client

from tenant_schemas.test.mixins import TenantRequestFactoryMixin


class TenantRequestFactory(TenantRequestFactoryMixin, RequestFactory):
    pass


class TenantClient(TenantRequestFactoryMixin, Client):
    pass