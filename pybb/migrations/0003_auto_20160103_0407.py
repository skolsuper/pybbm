# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('pybb', '0002_auto_20151231_2326'),
    ]

    operations = [
        migrations.AlterField(
            model_name='post',
            name='user',
            field=models.ForeignKey(related_name='posts', verbose_name='User', to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AlterField(
            model_name='topic',
            name='forum',
            field=models.ForeignKey(related_name='+', verbose_name='Forum', to='pybb.Forum'),
        ),
    ]
