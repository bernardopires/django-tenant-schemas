from django.contrib.auth.models import User
from django.db import models


class DummyModel(models.Model):
    """
    Just a test model so we can test manipulating data inside a tenant
    """
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name


class ModelWithFkToPublicUser(models.Model):
    user = models.ForeignKey(User)
