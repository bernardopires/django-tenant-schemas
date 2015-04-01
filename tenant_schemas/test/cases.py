from django.test import TestCase

from tenant_schemas.test.mixins import TenantTestCaseMixin


class TenantTestCase(TenantTestCaseMixin, TestCase):
    pass