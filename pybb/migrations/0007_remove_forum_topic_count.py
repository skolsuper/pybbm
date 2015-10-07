# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pybb', '0006_auto_20151007_0006'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='forum',
            name='topic_count',
        ),
    ]
