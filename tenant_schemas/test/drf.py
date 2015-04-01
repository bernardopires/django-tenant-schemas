from rest_framework.test import APIRequestFactory, APIClient, APITestCase

from tenant_schemas.test.mixins import TenantRequestFactoryMixin, TenantTestCaseMixin


class APITenantRequestFactory(TenantRequestFactoryMixin, APIRequestFactory):
    pass


class APITenantClient(TenantRequestFactoryMixin, APIClient):
    pass


class APITenantTestCase(TenantTestCaseMixin, APITestCase):
    client_class = APITenantClient