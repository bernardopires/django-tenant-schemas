from rest_framework.test import APITestCase

from tenant_schemas.test.mixins import TenantTestCaseMixin
from tenant_schemas.test.drf.client import APIClient


class APITenantTestCase(TenantTestCaseMixin, APITestCase):
    client_class = APIClient