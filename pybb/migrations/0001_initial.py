# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-05-09 06:51
from __future__ import unicode_literals

import annoying.fields
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import pybb.util


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80, verbose_name='Name')),
                ('position', models.IntegerField(blank=True, default=0, verbose_name='Position')),
                ('hidden', models.BooleanField(default=False, help_text='If checked, this category will be visible only for staff', verbose_name='Hidden')),
                ('slug', models.SlugField(max_length=255, unique=True, verbose_name='Slug')),
            ],
            options={
                'verbose_name_plural': 'Categories',
                'verbose_name': 'Category',
                'ordering': ['position'],
            },
        ),
        migrations.CreateModel(
            name='Forum',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80, verbose_name='Name')),
                ('position', models.IntegerField(blank=True, default=0, verbose_name='Position')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('hidden', models.BooleanField(default=False, verbose_name='Hidden')),
                ('headline', models.TextField(blank=True, null=True, verbose_name='Headline')),
                ('slug', models.SlugField(max_length=255, verbose_name='Slug')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='forums', to='pybb.Category', verbose_name='Category')),
                ('moderators', models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL, verbose_name='Moderators')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='child_forums', to='pybb.Forum', verbose_name='Parent forum')),
            ],
            options={
                'verbose_name_plural': 'Forums',
                'verbose_name': 'Forum',
                'ordering': ['position'],
            },
        ),
        migrations.CreateModel(
            name='ForumReadTracker',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time_stamp', models.DateTimeField(null=True)),
                ('forum', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pybb.Forum')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Forum read trackers',
                'verbose_name': 'Forum read tracker',
            },
        ),
        migrations.CreateModel(
            name='PollAnswer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=255, verbose_name='Text')),
            ],
            options={
                'verbose_name_plural': 'Polls answers',
                'verbose_name': 'Poll answer',
            },
        ),
        migrations.CreateModel(
            name='PollAnswerUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('poll_answer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='users', to='pybb.PollAnswer', verbose_name='Poll answer')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='poll_answers', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name_plural': 'Polls answers users',
                'verbose_name': 'Poll answer user',
            },
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body', models.TextField(verbose_name='Message')),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Created')),
                ('updated', models.DateTimeField(blank=True, db_index=True, default=django.utils.timezone.now, verbose_name='Updated')),
                ('user_ip', models.GenericIPAddressField(verbose_name='User IP')),
                ('on_moderation', models.BooleanField(default=False, verbose_name='On moderation')),
                ('attachment', models.FileField(blank=True, upload_to=pybb.util.FilePathGenerator(to='pybb_upload/attachments'), verbose_name='Attachment')),
            ],
            options={
                'verbose_name_plural': 'Posts',
                'verbose_name': 'Post',
                'ordering': ['created'],
            },
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('signature', models.TextField(blank=True, max_length=1024, verbose_name='Signature')),
                ('time_zone', models.FloatField(choices=[(-12.0, '-12'), (-11.0, '-11'), (-10.0, '-10'), (-9.5, '-09.5'), (-9.0, '-09'), (-8.5, '-08.5'), (-8.0, '-08 PST'), (-7.0, '-07 MST'), (-6.0, '-06 CST'), (-5.0, '-05 EST'), (-4.0, '-04 AST'), (-3.5, '-03.5'), (-3.0, '-03 ADT'), (-2.0, '-02'), (-1.0, '-01'), (0.0, '00 GMT'), (1.0, '+01 CET'), (2.0, '+02'), (3.0, '+03'), (3.5, '+03.5'), (4.0, '+04'), (4.5, '+04.5'), (5.0, '+05'), (5.5, '+05.5'), (6.0, '+06'), (6.5, '+06.5'), (7.0, '+07'), (8.0, '+08'), (9.0, '+09'), (9.5, '+09.5'), (10.0, '+10'), (10.5, '+10.5'), (11.0, '+11'), (11.5, '+11.5'), (12.0, '+12'), (13.0, '+13'), (14.0, '+14')], default=3.0, verbose_name='Time zone')),
                ('language', models.CharField(blank=True, choices=[('af', 'Afrikaans'), ('ar', 'Arabic'), ('ast', 'Asturian'), ('az', 'Azerbaijani'), ('bg', 'Bulgarian'), ('be', 'Belarusian'), ('bn', 'Bengali'), ('br', 'Breton'), ('bs', 'Bosnian'), ('ca', 'Catalan'), ('cs', 'Czech'), ('cy', 'Welsh'), ('da', 'Danish'), ('de', 'German'), ('el', 'Greek'), ('en', 'English'), ('en-au', 'Australian English'), ('en-gb', 'British English'), ('eo', 'Esperanto'), ('es', 'Spanish'), ('es-ar', 'Argentinian Spanish'), ('es-co', 'Colombian Spanish'), ('es-mx', 'Mexican Spanish'), ('es-ni', 'Nicaraguan Spanish'), ('es-ve', 'Venezuelan Spanish'), ('et', 'Estonian'), ('eu', 'Basque'), ('fa', 'Persian'), ('fi', 'Finnish'), ('fr', 'French'), ('fy', 'Frisian'), ('ga', 'Irish'), ('gd', 'Scottish Gaelic'), ('gl', 'Galician'), ('he', 'Hebrew'), ('hi', 'Hindi'), ('hr', 'Croatian'), ('hu', 'Hungarian'), ('ia', 'Interlingua'), ('id', 'Indonesian'), ('io', 'Ido'), ('is', 'Icelandic'), ('it', 'Italian'), ('ja', 'Japanese'), ('ka', 'Georgian'), ('kk', 'Kazakh'), ('km', 'Khmer'), ('kn', 'Kannada'), ('ko', 'Korean'), ('lb', 'Luxembourgish'), ('lt', 'Lithuanian'), ('lv', 'Latvian'), ('mk', 'Macedonian'), ('ml', 'Malayalam'), ('mn', 'Mongolian'), ('mr', 'Marathi'), ('my', 'Burmese'), ('nb', 'Norwegian Bokmal'), ('ne', 'Nepali'), ('nl', 'Dutch'), ('nn', 'Norwegian Nynorsk'), ('os', 'Ossetic'), ('pa', 'Punjabi'), ('pl', 'Polish'), ('pt', 'Portuguese'), ('pt-br', 'Brazilian Portuguese'), ('ro', 'Romanian'), ('ru', 'Russian'), ('sk', 'Slovak'), ('sl', 'Slovenian'), ('sq', 'Albanian'), ('sr', 'Serbian'), ('sr-latn', 'Serbian Latin'), ('sv', 'Swedish'), ('sw', 'Swahili'), ('ta', 'Tamil'), ('te', 'Telugu'), ('th', 'Thai'), ('tr', 'Turkish'), ('tt', 'Tatar'), ('udm', 'Udmurt'), ('uk', 'Ukrainian'), ('ur', 'Urdu'), ('vi', 'Vietnamese'), ('zh-hans', 'Simplified Chinese'), ('zh-hant', 'Traditional Chinese')], default='en-us', max_length=10, verbose_name='Language')),
                ('show_signatures', models.BooleanField(default=True, verbose_name='Show signatures')),
                ('avatar', models.ImageField(blank=True, null=True, upload_to=pybb.util.FilePathGenerator(to='pybb/avatar'), verbose_name='Avatar')),
                ('autosubscribe', models.BooleanField(default=True, help_text='Automatically subscribe to topics that you answer', verbose_name='Automatically subscribe')),
                ('user', annoying.fields.AutoOneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='pybb_profile', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name_plural': 'Profiles',
                'verbose_name': 'Profile',
            },
        ),
        migrations.CreateModel(
            name='Topic',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Subject')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('views', models.IntegerField(blank=True, default=0, verbose_name='Views count')),
                ('sticky', models.BooleanField(default=False, verbose_name='Sticky')),
                ('closed', models.BooleanField(default=False, verbose_name='Closed')),
                ('on_moderation', models.BooleanField(default=False, verbose_name='On moderation')),
                ('poll_type', models.IntegerField(choices=[(0, 'None'), (1, 'Single answer'), (2, 'Multiple answers')], default=0, verbose_name='Poll type')),
                ('poll_question', models.TextField(blank=True, null=True, verbose_name='Poll question')),
                ('slug', models.SlugField(max_length=255, verbose_name='Slug')),
                ('forum', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='pybb.Forum', verbose_name='Forum')),
            ],
            options={
                'verbose_name_plural': 'Topics',
                'verbose_name': 'Topic',
                'ordering': ['-created'],
            },
        ),
        migrations.CreateModel(
            name='TopicReadTracker',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time_stamp', models.DateTimeField(null=True)),
                ('topic', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pybb.Topic')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Topic read trackers',
                'verbose_name': 'Topic read tracker',
            },
        ),
        migrations.AddField(
            model_name='topic',
            name='readed_by',
            field=models.ManyToManyField(related_name='readed_topics', through='pybb.TopicReadTracker', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='topic',
            name='subscribers',
            field=models.ManyToManyField(blank=True, related_name='subscriptions', to=settings.AUTH_USER_MODEL, verbose_name='Subscribers'),
        ),
        migrations.AddField(
            model_name='topic',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='topics', to=settings.AUTH_USER_MODEL, verbose_name='User'),
        ),
        migrations.AddField(
            model_name='post',
            name='topic',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='posts', to='pybb.Topic', verbose_name='Topic'),
        ),
        migrations.AddField(
            model_name='post',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='posts', to=settings.AUTH_USER_MODEL, verbose_name='User'),
        ),
        migrations.AddField(
            model_name='pollanswer',
            name='topic',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='poll_answers', to='pybb.Topic', verbose_name='Topic'),
        ),
        migrations.AddField(
            model_name='forum',
            name='readed_by',
            field=models.ManyToManyField(related_name='readed_forums', through='pybb.ForumReadTracker', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='topicreadtracker',
            unique_together=set([('user', 'topic')]),
        ),
        migrations.AlterUniqueTogether(
            name='topic',
            unique_together=set([('forum', 'slug')]),
        ),
        migrations.AlterUniqueTogether(
            name='pollansweruser',
            unique_together=set([('poll_answer', 'user')]),
        ),
        migrations.AlterUniqueTogether(
            name='forumreadtracker',
            unique_together=set([('user', 'forum')]),
        ),
        migrations.AlterUniqueTogether(
            name='forum',
            unique_together=set([('category', 'slug')]),
        ),
    ]
