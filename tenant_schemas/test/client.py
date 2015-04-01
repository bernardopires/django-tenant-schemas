from django.test import RequestFactory, Client

from tenant_schemas.test.mixins import TenantRequestFactoryMixin, TenantClientMixin


class TenantRequestFactory(TenantRequestFactoryMixin, RequestFactory):
    pass


class TenantClient(TenantClientMixin, Client):
    pass