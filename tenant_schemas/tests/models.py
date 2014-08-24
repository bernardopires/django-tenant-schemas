from django.db import models
from tenant_schemas.models import TenantMixin


# as TenantMixin is an abstract model, it needs to be created
class Tenant(TenantMixin):
    pass

    class Meta:
        app_label = 'tenant_schemas'


class NonAutoSyncTenant(TenantMixin):
    auto_create_schema = False

    class Meta:
        app_label = 'tenant_schemas'


class DummyModel(models.Model):
    """
    Just a test model so we can test manipulating data
    inside a tenant
    """
    name = models.CharField(max_length=1337)  # every dummy should have a pretty name :)

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'tenant_schemas'