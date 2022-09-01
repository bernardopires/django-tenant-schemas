from django.dispatch import Signal

try:
    # Django < 4.0
    post_schema_sync = Signal(providing_args=['tenant'])
except TypeError:
    post_schema_sync = Signal()
post_schema_sync.__doc__ = """
Sent after a tenant has been saved, its schema created and synced
"""
