# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pybb', '0008_remove_topic_post_count'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='forum',
            name='post_count',
        ),
    ]
