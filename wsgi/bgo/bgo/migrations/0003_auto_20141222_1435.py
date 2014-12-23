# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bgo', '0002_auto_20141222_1201'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='testresult',
            unique_together=set([('test', 'component', 'name', 'result')]),
        ),
    ]
