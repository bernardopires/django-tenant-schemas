import logging

from django.db import connection, connections, router


class TenantContextFilter(logging.Filter):
    """
    Add the current ``schema_name`` and ``domain_url`` to log records.

    Thanks to @regolith for the snippet on #248
    """
    def filter(self, record):
    	db = router.db_for_read(None)
        record.schema_name = connections[db].tenant.schema_name
        record.domain_url = getattr(connections[db].tenant, 'domain_url', '')
        return True
