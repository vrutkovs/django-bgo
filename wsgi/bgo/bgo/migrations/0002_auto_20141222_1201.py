# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bgo', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='build',
            name='tests_were_parsed',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='test',
            name='test_results_were_parsed',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='test',
            name='start_date',
            field=models.DateTimeField(),
            preserve_default=True,
        ),
    ]
