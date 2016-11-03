import logging
from mock import patch

from django.test import TestCase

from tenant_schemas import log


@patch('tenant_schemas.log.connection.tenant', autospec=True,
       schema_name='context')
class LoggingFilterTests(TestCase):

    def test_tenant_context_filter(self, mock_connection):
        mock_connection.domain_url = 'context.example.com'
        filter_ = log.TenantContextFilter()
        record = logging.makeLogRecord({})
        res = filter_.filter(record)
        self.assertEqual(res, True)
        self.assertEqual(record.schema_name, 'context')
        self.assertEqual(record.domain_url, 'context.example.com')

    def test_tenant_context_filter_blank_domain_url(self, mock_connection):
        filter_ = log.TenantContextFilter()
        record = logging.makeLogRecord({})
        res = filter_.filter(record)
        self.assertEqual(res, True)
        self.assertEqual(record.schema_name, 'context')
        self.assertEqual(record.domain_url, '')
