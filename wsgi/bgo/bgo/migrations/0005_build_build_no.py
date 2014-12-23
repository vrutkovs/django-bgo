# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bgo', '0004_auto_20141223_1231'),
    ]

    operations = [
        migrations.AddField(
            model_name='build',
            name='build_no',
            field=models.IntegerField(default=0),
            preserve_default=True,
        ),
    ]
