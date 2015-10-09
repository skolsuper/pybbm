# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('pybb', '0010_remove_profile_post_count'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='forum',
            name='updated',
        ),
        migrations.RemoveField(
            model_name='topic',
            name='updated',
        ),
        migrations.AlterField(
            model_name='post',
            name='updated',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Updated', blank=True),
        ),
    ]
