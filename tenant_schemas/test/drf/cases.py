from rest_framework.test import APITestCase

from tenant_schemas.test.mixins import TenantTestCaseMixin
from tenant_schemas.test.drf.client import APITenantClient


class APITenantTestCase(TenantTestCaseMixin, APITestCase):
    client_class = APITenantClient