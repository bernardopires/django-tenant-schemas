from django.db.models.signals import post_delete
from django.dispatch import receiver
from tenant_schemas.utils import schema_exists, get_tenant_model
from django.db import connection


@receiver(post_delete, sender=get_tenant_model())
def drop_schema(sender, instance, **kwargs):
    """
    Called in post_delete signal.
    Drops the schema related to the tenant instance. Just drop the schema if the parent
    class model has the attribute auto_drop_schema set to True.
    """
    if schema_exists(instance.schema_name) and instance.auto_drop_schema:
        cursor = connection.cursor()
        cursor.execute('DROP SCHEMA %s CASCADE' % instance.schema_name)
