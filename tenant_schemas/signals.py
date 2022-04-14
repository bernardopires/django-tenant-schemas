from django.dispatch import Signal

try:
    post_schema_sync = Signal(providing_args=['tenant'])
except:
    post_schema_sync = Signal()    
post_schema_sync.__doc__ = """
Sent after a tenant has been saved, its schema created and synced
"""
