# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pybb', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='forum',
            name='post_count',
        ),
        migrations.RemoveField(
            model_name='forum',
            name='topic_count',
        ),
        migrations.RemoveField(
            model_name='forum',
            name='updated',
        ),
    ]
