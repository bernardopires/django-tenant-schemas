from django.dispatch import Signal

post_schema_sync = Signal(providing_args=['tenant'])
post_schema_sync.__doc__ = """
Sent after a tenant has been saved, its schema created and synced
"""
