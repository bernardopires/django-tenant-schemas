import logging

from django.db import connection


class TenantContextFilter(logging.Filter):
    """
    Add the current ``schema_name`` and ``domain_url`` to log records.

    Thanks to @regolith for the snippet on #248
    """
    def filter(self, record):
        record.schema_name = connection.tenant.schema_name
        record.domain_url = getattr(connection.tenant, 'domain_url', '')
        return True
