# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pybb', '0007_remove_forum_topic_count'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='topic',
            name='post_count',
        ),
    ]
