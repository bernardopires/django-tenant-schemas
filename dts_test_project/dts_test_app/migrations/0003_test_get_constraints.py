# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django

from django.db import models, migrations
from django.conf import settings

# Class-based indexes were added in Django 1.11. This try/except block can be
# removed when support for Django 1.8 is dropped.
try:
    from django.contrib.postgres.indexes import BrinIndex
except ImportError:
    pass


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dts_test_app', '0002_test_drop_unique'),
    ]

    def __init__(self, *args, **kwargs):
        super(Migration, self).__init__(*args, **kwargs)

        # The assignment of operations can be moved to the class definition
        # when support for Django 1.8 is dropped.
        if django.VERSION >= (1, 11, 0):
            self.operations = [
                migrations.AddField(
                    model_name='DummyModel',
                    name='indexed',
                    field=models.CharField(max_length=100)
                ),

                migrations.AlterField(
                    model_name='DummyModel',
                    name='indexed',
                    field=models.CharField(
                        max_length=100,
                        db_index=True,
                    ),
                ),

                migrations.AlterField(
                    model_name='DummyModel',
                    name='indexed',
                    field=models.CharField(
                        max_length=100,
                        db_index=True,
                        unique=True,
                    ),
                ),

                migrations.AlterField(
                    model_name='DummyModel',
                    name='indexed',
                    field=models.CharField(max_length=100),
                ),

                migrations.AddIndex(
                    model_name='dummymodel',
                    index=BrinIndex(
                        fields=['indexed'],
                        name='indexed_brin',
                    ),
                ),

                migrations.RemoveIndex(
                    model_name='dummymodel',
                    name='indexed_brin',
                ),

                migrations.RemoveField(
                    model_name='DummyModel',
                    name='indexed',
                ),
            ]
