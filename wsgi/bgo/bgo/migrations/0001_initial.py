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
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('build_no', models.IntegerField(default=0)),
                ('start_date', models.DateTimeField()),
                ('completed', models.BooleanField(default=1)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Test',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('start_date', models.DateTimeField()),
                ('duration', models.IntegerField(default=0)),
                ('results', models.IntegerField(default=0)),
                ('success', models.BooleanField(default=False)),
                ('build', models.ForeignKey(to='bgo.Build')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TestResult',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
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
