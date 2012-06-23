from django.db import models

class TenantMixin(models.Model):
    domain_url = models.CharField(max_length=128, unique=True)
    schema_name = models.CharField(max_length=63)

    class Meta:
        abstract = True