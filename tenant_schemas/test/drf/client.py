from rest_framework.test import APIRequestFactory, APIClient

from tenant_schemas.test.mixins import TenantRequestFactoryMixin, TenantClientMixin


class APITenantRequestFactory(TenantRequestFactoryMixin, APIRequestFactory):
    pass


class APITenantClient(TenantClientMixin, TenantRequestFactoryMixin, APIClient):
    pass