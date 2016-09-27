import logging

from django.test import TestCase

from tenant_schemas import log


class LoggingFilterTests(TestCase):

    def test_tenant_context_filter(self):
        filter_ = log.TenantContextFilter()
        record = logging.makeLogRecord({})
        res = filter_.filter(record)
        self.assertEqual(res, True)
        self.assertEqual(record.schema_name, 'public')
        self.assertEqual(record.domain_url, '')
