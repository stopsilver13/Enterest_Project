# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-08-21 10:21
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sharespot', '0002_auto_20180821_0800'),
    ]

    operations = [
        migrations.AddField(
            model_name='seatlevel',
            name='hover_color',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]
