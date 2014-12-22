# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Build',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, verbose_name='ID', serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('start_date', models.DateTimeField(verbose_name='date published')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Test',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, verbose_name='ID', serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('start_date', models.DateTimeField(verbose_name='date published')),
                ('duration', models.IntegerField(default=0)),
                ('results', models.IntegerField(default=0)),
                ('screenshot', models.URLField()),
                ('build', models.ForeignKey(to='bgo.Build')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TestResult',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, verbose_name='ID', serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('component', models.CharField(max_length=200)),
                ('result', models.IntegerField(default=0)),
                ('test', models.ForeignKey(to='bgo.Test')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
