from django.test import TestCase

from tenant_schemas.test.mixins import TenantTestCaseMixin
from tenant_schemas.test.client import TenantClient


class TenantTestCase(TenantTestCaseMixin, TestCase):
    client_class = TenantClient