# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bgo', '0003_auto_20141222_1435'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='build',
            name='tests_were_parsed',
        ),
        migrations.RemoveField(
            model_name='test',
            name='test_results_were_parsed',
        ),
        migrations.AlterUniqueTogether(
            name='testresult',
            unique_together=set([]),
        ),
    ]
