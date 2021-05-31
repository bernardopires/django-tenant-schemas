# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dts_test_app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='DummyModel',
            name='unique_value',
            field=models.IntegerField(blank=True, null=True, unique=True),
        ),

        migrations.AlterField(
            model_name='DummyModel',
            name='unique_value',
            field=models.IntegerField(blank=True, null=True),
        ),

        migrations.RemoveField(
            model_name='DummyModel',
            name='unique_value',
        ),
    ]
