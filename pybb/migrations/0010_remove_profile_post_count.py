# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pybb', '0009_remove_forum_post_count'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='post_count',
        ),
    ]
