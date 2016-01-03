# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
from django.conf import settings
import pybb.util
import annoying.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Attachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('size', models.IntegerField(verbose_name='Size')),
                ('file', models.FileField(upload_to=pybb.util.FilePathGenerator(to=b'pybb_upload/attachments'), verbose_name='File')),
            ],
            options={
                'verbose_name': 'Attachment',
                'verbose_name_plural': 'Attachments',
            },
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=80, verbose_name='Name')),
                ('position', models.IntegerField(default=0, verbose_name='Position', blank=True)),
                ('hidden', models.BooleanField(default=False, help_text='If checked, this category will be visible only for staff', verbose_name='Hidden')),
                ('slug', models.SlugField(unique=True, max_length=255, verbose_name='Slug')),
            ],
            options={
                'ordering': ['position'],
                'verbose_name': 'Category',
                'verbose_name_plural': 'Categories',
            },
        ),
        migrations.CreateModel(
            name='Forum',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=80, verbose_name='Name')),
                ('position', models.IntegerField(default=0, verbose_name='Position', blank=True)),
                ('description', models.TextField(verbose_name='Description', blank=True)),
                ('hidden', models.BooleanField(default=False, verbose_name='Hidden')),
                ('headline', models.TextField(null=True, verbose_name='Headline', blank=True)),
                ('slug', models.SlugField(max_length=255, verbose_name='Slug')),
                ('category', models.ForeignKey(related_name='forums', verbose_name='Category', to='pybb.Category')),
                ('moderators', models.ManyToManyField(to=settings.AUTH_USER_MODEL, verbose_name='Moderators', blank=True)),
                ('parent', models.ForeignKey(related_name='child_forums', verbose_name='Parent forum', blank=True, to='pybb.Forum', null=True)),
            ],
            options={
                'ordering': ['position'],
                'verbose_name': 'Forum',
                'verbose_name_plural': 'Forums',
            },
        ),
        migrations.CreateModel(
            name='ForumReadTracker',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('time_stamp', models.DateTimeField(auto_now=True)),
                ('forum', models.ForeignKey(blank=True, to='pybb.Forum', null=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Forum read tracker',
                'verbose_name_plural': 'Forum read trackers',
            },
        ),
        migrations.CreateModel(
            name='PollAnswer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.CharField(max_length=255, verbose_name='Text')),
            ],
            options={
                'verbose_name': 'Poll answer',
                'verbose_name_plural': 'Polls answers',
            },
        ),
        migrations.CreateModel(
            name='PollAnswerUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('poll_answer', models.ForeignKey(related_name='users', verbose_name='Poll answer', to='pybb.PollAnswer')),
                ('user', models.ForeignKey(related_name='poll_answers', verbose_name='User', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Poll answer user',
                'verbose_name_plural': 'Polls answers users',
            },
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('body', models.TextField(verbose_name='Message')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created', db_index=True)),
                ('updated', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Updated', blank=True)),
                ('user_ip', models.IPAddressField(default='0.0.0.0', verbose_name='User IP', blank=True)),
                ('on_moderation', models.BooleanField(default=False, verbose_name='On moderation')),
            ],
            options={
                'ordering': ['created'],
                'verbose_name': 'Post',
                'verbose_name_plural': 'Posts',
            },
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('signature', models.TextField(max_length=1024, verbose_name='Signature', blank=True)),
                ('signature_html', models.TextField(max_length=1054, verbose_name='Signature HTML Version', blank=True)),
                ('time_zone', models.FloatField(default=3.0, verbose_name='Time zone', choices=[(-12.0, '-12'), (-11.0, '-11'), (-10.0, '-10'), (-9.5, '-09.5'), (-9.0, '-09'), (-8.5, '-08.5'), (-8.0, '-08 PST'), (-7.0, '-07 MST'), (-6.0, '-06 CST'), (-5.0, '-05 EST'), (-4.0, '-04 AST'), (-3.5, '-03.5'), (-3.0, '-03 ADT'), (-2.0, '-02'), (-1.0, '-01'), (0.0, '00 GMT'), (1.0, '+01 CET'), (2.0, '+02'), (3.0, '+03'), (3.5, '+03.5'), (4.0, '+04'), (4.5, '+04.5'), (5.0, '+05'), (5.5, '+05.5'), (6.0, '+06'), (6.5, '+06.5'), (7.0, '+07'), (8.0, '+08'), (9.0, '+09'), (9.5, '+09.5'), (10.0, '+10'), (10.5, '+10.5'), (11.0, '+11'), (11.5, '+11.5'), (12.0, '+12'), (13.0, '+13'), (14.0, '+14')])),
                ('language', models.CharField(default='en-us', max_length=10, verbose_name='Language', blank=True, choices=[(b'af', b'Afrikaans'), (b'ar', b'Arabic'), (b'ast', b'Asturian'), (b'az', b'Azerbaijani'), (b'bg', b'Bulgarian'), (b'be', b'Belarusian'), (b'bn', b'Bengali'), (b'br', b'Breton'), (b'bs', b'Bosnian'), (b'ca', b'Catalan'), (b'cs', b'Czech'), (b'cy', b'Welsh'), (b'da', b'Danish'), (b'de', b'German'), (b'el', b'Greek'), (b'en', b'English'), (b'en-au', b'Australian English'), (b'en-gb', b'British English'), (b'eo', b'Esperanto'), (b'es', b'Spanish'), (b'es-ar', b'Argentinian Spanish'), (b'es-mx', b'Mexican Spanish'), (b'es-ni', b'Nicaraguan Spanish'), (b'es-ve', b'Venezuelan Spanish'), (b'et', b'Estonian'), (b'eu', b'Basque'), (b'fa', b'Persian'), (b'fi', b'Finnish'), (b'fr', b'French'), (b'fy', b'Frisian'), (b'ga', b'Irish'), (b'gl', b'Galician'), (b'he', b'Hebrew'), (b'hi', b'Hindi'), (b'hr', b'Croatian'), (b'hu', b'Hungarian'), (b'ia', b'Interlingua'), (b'id', b'Indonesian'), (b'io', b'Ido'), (b'is', b'Icelandic'), (b'it', b'Italian'), (b'ja', b'Japanese'), (b'ka', b'Georgian'), (b'kk', b'Kazakh'), (b'km', b'Khmer'), (b'kn', b'Kannada'), (b'ko', b'Korean'), (b'lb', b'Luxembourgish'), (b'lt', b'Lithuanian'), (b'lv', b'Latvian'), (b'mk', b'Macedonian'), (b'ml', b'Malayalam'), (b'mn', b'Mongolian'), (b'mr', b'Marathi'), (b'my', b'Burmese'), (b'nb', b'Norwegian Bokmal'), (b'ne', b'Nepali'), (b'nl', b'Dutch'), (b'nn', b'Norwegian Nynorsk'), (b'os', b'Ossetic'), (b'pa', b'Punjabi'), (b'pl', b'Polish'), (b'pt', b'Portuguese'), (b'pt-br', b'Brazilian Portuguese'), (b'ro', b'Romanian'), (b'ru', b'Russian'), (b'sk', b'Slovak'), (b'sl', b'Slovenian'), (b'sq', b'Albanian'), (b'sr', b'Serbian'), (b'sr-latn', b'Serbian Latin'), (b'sv', b'Swedish'), (b'sw', b'Swahili'), (b'ta', b'Tamil'), (b'te', b'Telugu'), (b'th', b'Thai'), (b'tr', b'Turkish'), (b'tt', b'Tatar'), (b'udm', b'Udmurt'), (b'uk', b'Ukrainian'), (b'ur', b'Urdu'), (b'vi', b'Vietnamese'), (b'zh-cn', b'Simplified Chinese'), (b'zh-hans', b'Simplified Chinese'), (b'zh-hant', b'Traditional Chinese'), (b'zh-tw', b'Traditional Chinese')])),
                ('show_signatures', models.BooleanField(default=True, verbose_name='Show signatures')),
                ('avatar', models.ImageField(upload_to=pybb.util.FilePathGenerator(to='pybb/avatar'), null=True, verbose_name='Avatar', blank=True)),
                ('autosubscribe', models.BooleanField(default=True, help_text='Automatically subscribe to topics that you answer', verbose_name='Automatically subscribe')),
                ('user', annoying.fields.AutoOneToOneField(related_name='pybb_profile', verbose_name='User', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Profile',
                'verbose_name_plural': 'Profiles',
            },
        ),
        migrations.CreateModel(
            name='Topic',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='Subject')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('views', models.IntegerField(default=0, verbose_name='Views count', blank=True)),
                ('sticky', models.BooleanField(default=False, verbose_name='Sticky')),
                ('closed', models.BooleanField(default=False, verbose_name='Closed')),
                ('on_moderation', models.BooleanField(default=False, verbose_name='On moderation')),
                ('poll_type', models.IntegerField(default=0, verbose_name='Poll type', choices=[(0, 'None'), (1, 'Single answer'), (2, 'Multiple answers')])),
                ('poll_question', models.TextField(null=True, verbose_name='Poll question', blank=True)),
                ('slug', models.SlugField(max_length=255, verbose_name='Slug')),
                ('forum', models.ForeignKey(related_name='+', verbose_name='Forum', to='pybb.Forum')),
            ],
            options={
                'ordering': ['-created'],
                'verbose_name': 'Topic',
                'verbose_name_plural': 'Topics',
            },
        ),
        migrations.CreateModel(
            name='TopicReadTracker',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('time_stamp', models.DateTimeField(auto_now=True)),
                ('topic', models.ForeignKey(blank=True, to='pybb.Topic', null=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Topic read tracker',
                'verbose_name_plural': 'Topic read trackers',
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
            field=models.ManyToManyField(related_name='subscriptions', verbose_name='Subscribers', to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AddField(
            model_name='topic',
            name='user',
            field=models.ForeignKey(related_name='topics', verbose_name='User', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='post',
            name='topic',
            field=models.ForeignKey(related_name='posts', verbose_name='Topic', to='pybb.Topic'),
        ),
        migrations.AddField(
            model_name='post',
            name='user',
            field=models.ForeignKey(related_name='posts', verbose_name='User', to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AddField(
            model_name='pollanswer',
            name='topic',
            field=models.ForeignKey(related_name='poll_answers', verbose_name='Topic', to='pybb.Topic'),
        ),
        migrations.AddField(
            model_name='forum',
            name='readed_by',
            field=models.ManyToManyField(related_name='readed_forums', through='pybb.ForumReadTracker', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='attachment',
            name='post',
            field=models.OneToOneField(related_name='attachment', verbose_name='Post', to='pybb.Post'),
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
