# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dts_test_app', '0004_test_alter_unique'),
    ]

    operations = [
        migrations.AlterField(
            model_name='DummyModel',
            name='id',
            field=models.IntegerField()
        ),
        migrations.AlterField(
            model_name='DummyModel',
            name='id',
            field=models.AutoField()
        ),
    ]
