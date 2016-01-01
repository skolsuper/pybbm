# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase, skipUnlessDBFeature, Client
from lxml import html

from pybb import util
from pybb.models import Forum, Topic, Post, TopicReadTracker, ForumReadTracker, Category
from pybb.settings import settings as pybb_settings
from pybb.templatetags.pybb_tags import pybb_topic_unread, pybb_is_topic_unread, pybb_forum_unread, \
    pybb_get_latest_topics, pybb_get_latest_posts
from pybb.tests.utils import SharedTestModule, Profile

User = get_user_model()


class FeaturesTest(TestCase, SharedTestModule):
    def setUp(self):
        self.ORIG_PYBB_ENABLE_ANONYMOUS_POST = pybb_settings.PYBB_ENABLE_ANONYMOUS_POST
        self.ORIG_PYBB_PREMODERATION = pybb_settings.PYBB_PREMODERATION
        pybb_settings.PYBB_PREMODERATION = False
        pybb_settings.PYBB_ENABLE_ANONYMOUS_POST = False
        self.create_user()
        self.create_initial()
        mail.outbox = []

    def test_base(self):
        # Check index page
        Forum.objects.create(name='xfoo1', description='bar1', category=self.category, parent=self.forum)
        url = reverse('pybb:index')
        response = self.client.get(url)
        parser = html.HTMLParser(encoding='utf8')
        tree = html.fromstring(response.content, parser=parser)
        self.assertContains(response, 'foo')
        self.assertContains(response, self.forum.get_absolute_url())
        self.assertTrue(pybb_settings.PYBB_DEFAULT_TITLE in tree.xpath('//title')[0].text_content())
        self.assertEqual(len(response.context['categories']), 1)
        self.assertEqual(len(response.context['categories'][0].forums_accessed), 1)

    def test_forum_page(self):
        # Check forum page
        response = self.client.get(self.forum.get_absolute_url())
        self.assertEqual(response.context['forum'], self.forum)
        tree = html.fromstring(response.content)
        self.assertTrue(tree.xpath('//a[@href="%s"]' % self.topic.get_absolute_url()))
        self.assertTrue(tree.xpath('//title[contains(text(),"%s")]' % self.forum.name))
        self.assertFalse(tree.xpath('//a[contains(@href,"?page=")]'))
        self.assertFalse(response.context['is_paginated'])

    def test_category_page(self):
        Forum.objects.create(name='xfoo1', description='bar1', category=self.category, parent=self.forum)
        response = self.client.get(self.category.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.forum.get_absolute_url())
        self.assertEqual(len(response.context['object'].forums_accessed), 1)

    def test_profile_language_default(self):
        user = User.objects.create_user(username='user2', password='user2', email='user2@example.com')
        self.assertEqual(util.get_pybb_profile(user).language, settings.LANGUAGE_CODE)

    def test_profile_edit(self):
        # Self profile edit
        self.login_client()
        response = self.client.get(reverse('pybb:edit_profile'))
        self.assertEqual(response.status_code, 200)
        values = self.get_form_values(response, 'profile-edit')
        values['signature'] = 'test signature'
        response = self.client.post(reverse('pybb:edit_profile'), data=values, follow=True)
        self.assertEqual(response.status_code, 200)
        self.client.get(self.post.get_absolute_url(), follow=True)
        self.assertContains(response, 'test signature')
        # Test empty signature
        values['signature'] = ''
        response = self.client.post(reverse('pybb:edit_profile'), data=values, follow=True)
        self.assertEqual(len(response.context['form'].errors), 0)

    def test_pagination_and_topic_addition(self):
        for i in range(0, pybb_settings.PYBB_FORUM_PAGE_SIZE + 3):
            topic = Topic(name='topic_%s_' % i, forum=self.forum, user=self.user)
            topic.save()
        url = self.forum.get_absolute_url()
        response = self.client.get(url)
        self.assertEqual(len(response.context['topic_list']), pybb_settings.PYBB_FORUM_PAGE_SIZE)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(response.context['paginator'].num_pages,
                         int((pybb_settings.PYBB_FORUM_PAGE_SIZE + 3) / pybb_settings.PYBB_FORUM_PAGE_SIZE) + 1)

    def test_bbcode_and_topic_title(self):
        response = self.client.get(self.topic.get_absolute_url())
        self.assertTrue('name' in response.data)
        self.assertEqual(response.data['posts'][0]['body'], self.post.body)

    def test_topic_addition(self):
        self.login_client()
        add_topic_url = reverse('pybb:add_topic', kwargs={'forum_id': self.forum.id})
        response = self.client.get(add_topic_url)
        values = self.get_form_values(response)
        values['body'] = 'new topic test'
        values['name'] = 'new topic name'
        values['poll_type'] = 0
        response = self.client.post(add_topic_url, data=values, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Topic.objects.filter(name='new topic name').exists())

    def test_post_deletion(self):
        post = Post(topic=self.topic, user=self.user, body='bbcode [b]test[/b]')
        post.save()
        post.delete()
        Topic.objects.get(id=self.topic.id)
        Forum.objects.get(id=self.forum.id)

    def test_topic_deletion(self):
        topic = Topic(name='xtopic', forum=self.forum, user=self.user)
        topic.save()
        post = Post(topic=topic, user=self.user, body='one')
        post.save()
        post = Post(topic=topic, user=self.user, body='two')
        post.save()
        post.delete()
        Topic.objects.get(id=topic.id)
        Forum.objects.get(id=self.forum.id)
        topic.delete()
        Forum.objects.get(id=self.forum.id)

    def test_forum_updated(self):
        topic = Topic(name='xtopic', forum=self.forum, user=self.user)
        topic.save()
        post = Post(topic=topic, user=self.user, body='one')
        post.save()
        post = Post.objects.get(id=post.id)
        self.assertAlmostEqual(self.forum.updated, post.created, delta=datetime.timedelta(milliseconds=50))

    @skipUnlessDBFeature('supports_microsecond_precision')
    def test_read_tracking(self):
        topic = Topic(name='xtopic', forum=self.forum, user=self.user)
        topic.save()
        post = Post(topic=topic, user=self.user, body='one')
        post.save()
        client = Client()
        client.login(username='zeus', password='zeus')
        # Topic status
        tree = html.fromstring(client.get(topic.forum.get_absolute_url()).content)
        self.assertTrue(tree.xpath('//a[@href="%s"]/parent::td[contains(@class,"unread")]' % topic.get_absolute_url()))
        # Forum status
        tree = html.fromstring(client.get(reverse('pybb:index')).content)
        self.assertTrue(
            tree.xpath('//a[@href="%s"]/parent::td[contains(@class,"unread")]' % topic.forum.get_absolute_url()))
        # Visit it
        client.get(topic.get_absolute_url())
        # Topic status - readed
        tree = html.fromstring(client.get(topic.forum.get_absolute_url()).content)
        # Visit others
        for t in topic.forum.topics.all():
            client.get(t.get_absolute_url())
        self.assertFalse(tree.xpath('//a[@href="%s"]/parent::td[contains(@class,"unread")]' % topic.get_absolute_url()))
        # Forum status - readed
        tree = html.fromstring(client.get(reverse('pybb:index')).content)
        self.assertFalse(
            tree.xpath('//a[@href="%s"]/parent::td[contains(@class,"unread")]' % topic.forum.get_absolute_url()))
        # Post message
        add_post_url = reverse('pybb:add_post', kwargs={'topic_id': topic.id})
        response = client.get(add_post_url)
        values = self.get_form_values(response)
        values['body'] = 'test tracking'
        response = client.post(add_post_url, values, follow=True)
        self.assertContains(response, 'test tracking')
        # Topic status - readed
        tree = html.fromstring(client.get(topic.forum.get_absolute_url()).content)
        self.assertFalse(tree.xpath('//a[@href="%s"]/parent::td[contains(@class,"unread")]' % topic.get_absolute_url()))
        # Forum status - readed
        tree = html.fromstring(client.get(reverse('pybb:index')).content)
        self.assertFalse(
            tree.xpath('//a[@href="%s"]/parent::td[contains(@class,"unread")]' % topic.forum.get_absolute_url()))
        post = Post(topic=topic, user=self.user, body='one')
        post.save()
        client.get(reverse('pybb:mark_all_as_read'))
        tree = html.fromstring(client.get(reverse('pybb:index')).content)
        self.assertFalse(
            tree.xpath('//a[@href="%s"]/parent::td[contains(@class,"unread")]' % topic.forum.get_absolute_url()))
        # Empty forum - readed
        f = Forum(name='empty', category=self.category)
        f.save()
        tree = html.fromstring(client.get(reverse('pybb:index')).content)
        self.assertFalse(tree.xpath('//a[@href="%s"]/parent::td[contains(@class,"unread")]' % f.get_absolute_url()))

    @skipUnlessDBFeature('supports_microsecond_precision')
    def test_read_tracking_multi_user(self):
        topic_1 = self.topic
        topic_2 = Topic(name='topic_2', forum=self.forum, user=self.user)
        topic_2.save()

        Post(topic=topic_2, user=self.user, body='one').save()

        user_ann = User.objects.create_user('ann', 'ann@localhost', 'ann')
        client_ann = Client()
        client_ann.login(username='ann', password='ann')

        user_bob = User.objects.create_user('bob', 'bob@localhost', 'bob')
        client_bob = Client()
        client_bob.login(username='bob', password='bob')

        # Two topics, each with one post. everything is unread, so the db should reflect that:
        self.assertEqual(TopicReadTracker.objects.all().count(), 0)
        self.assertEqual(ForumReadTracker.objects.all().count(), 0)

        # user_ann reads topic_1, she should get one topic read tracker, there should be no forum read trackers
        client_ann.get(topic_1.get_absolute_url())
        self.assertEqual(TopicReadTracker.objects.all().count(), 1)
        self.assertEqual(TopicReadTracker.objects.filter(user=user_ann).count(), 1)
        self.assertEqual(TopicReadTracker.objects.filter(user=user_ann, topic=topic_1).count(), 1)
        self.assertEqual(ForumReadTracker.objects.all().count(), 0)

        # user_bob reads topic_1, he should get one topic read tracker, there should be no forum read trackers
        client_bob.get(topic_1.get_absolute_url())
        self.assertEqual(TopicReadTracker.objects.all().count(), 2)
        self.assertEqual(TopicReadTracker.objects.filter(user=user_bob).count(), 1)
        self.assertEqual(TopicReadTracker.objects.filter(user=user_bob, topic=topic_1).count(), 1)

        # user_bob reads topic_2, he should get a forum read tracker,
        #  there should be no topic read trackers for user_bob
        client_bob.get(topic_2.get_absolute_url())
        self.assertEqual(TopicReadTracker.objects.all().count(), 1)
        self.assertEqual(ForumReadTracker.objects.all().count(), 1)
        self.assertEqual(ForumReadTracker.objects.filter(user=user_bob).count(), 1)
        self.assertEqual(ForumReadTracker.objects.filter(user=user_bob, forum=self.forum).count(), 1)
        self.assertEqual(TopicReadTracker.objects.filter(user=user_bob).count(), 0)
        self.assertListEqual([t.unread for t in pybb_topic_unread([topic_1, topic_2], user_bob)], [False, False])

        # user_ann creates topic_3, they should get a new topic read tracker in the db
        add_topic_url = reverse('pybb:add_topic', kwargs={'forum_id': self.forum.id})
        response = client_ann.get(add_topic_url)
        values = self.get_form_values(response)
        values['body'] = 'topic_3'
        values['name'] = 'topic_3'
        values['poll_type'] = 0
        response = client_ann.post(add_topic_url, data=values, follow=True)
        self.assertEqual(TopicReadTracker.objects.all().count(), 2)
        self.assertEqual(TopicReadTracker.objects.filter(user=user_ann).count(), 2)
        self.assertEqual(ForumReadTracker.objects.all().count(), 1)
        topic_3 = Topic.objects.order_by('-posts__updated', '-id')[0]
        self.assertEqual(topic_3.name, 'topic_3')

        # user_ann posts to topic_1, a topic they've already read, no new trackers should be created
        add_post_url = reverse('pybb:add_post', kwargs={'topic_id': topic_1.id})
        response = client_ann.get(add_post_url)
        values = self.get_form_values(response)
        values['body'] = 'test tracking'
        response = client_ann.post(add_post_url, values, follow=True)
        self.assertEqual(TopicReadTracker.objects.all().count(), 2)
        self.assertEqual(TopicReadTracker.objects.filter(user=user_ann).count(), 2)
        self.assertEqual(ForumReadTracker.objects.all().count(), 1)

        # user_bob has two unread topics, 'topic_1' and 'topic_3'.
        #   This is because user_ann created a new topic and posted to an existing topic,
        #   after user_bob got his forum read tracker.

        # user_bob reads 'topic_1'
        #   user_bob gets a new topic read tracker, and the existing forum read tracker stays the same.
        #   'topic_3' appears unread for user_bob
        #
        previous_time = ForumReadTracker.objects.all()[0].time_stamp
        client_bob.get(topic_1.get_absolute_url())
        self.assertEqual(ForumReadTracker.objects.all().count(), 1)
        self.assertEqual(ForumReadTracker.objects.all()[0].time_stamp, previous_time)
        self.assertEqual(TopicReadTracker.objects.filter(user=user_bob).count(), 1)
        self.assertEqual(TopicReadTracker.objects.filter(user=user_ann).count(), 2)
        self.assertEqual(TopicReadTracker.objects.all().count(), 3)

        # user_bob reads the last unread topic, 'topic_3'.
        # user_bob's existing forum read tracker updates and his topic read tracker disappears
        #
        previous_time = ForumReadTracker.objects.all()[0].time_stamp
        client_bob.get(topic_3.get_absolute_url())
        self.assertEqual(ForumReadTracker.objects.all().count(), 1)
        self.assertGreater(ForumReadTracker.objects.all()[0].time_stamp, previous_time)
        self.assertEqual(TopicReadTracker.objects.all().count(), 2)
        self.assertEqual(TopicReadTracker.objects.filter(user=user_bob).count(), 0)

    def test_read_tracking_multi_forum(self):
        topic_1 = self.topic
        topic_2 = Topic(name='topic_2', forum=self.forum, user=self.user)
        topic_2.save()

        Post(topic=topic_2, user=self.user, body='one').save()

        forum_1 = self.forum
        forum_2 = Forum(name='forum_2', description='bar', category=self.category)
        forum_2.save()

        Topic(name='garbage', forum=forum_2, user=self.user).save()

        client = Client()
        client.login(username='zeus', password='zeus')

        # everything starts unread
        self.assertEqual(ForumReadTracker.objects.all().count(), 0)
        self.assertEqual(TopicReadTracker.objects.all().count(), 0)

        # user reads topic_1, they should get one topic read tracker, there should be no forum read trackers
        client.get(topic_1.get_absolute_url())
        self.assertEqual(TopicReadTracker.objects.all().count(), 1)
        self.assertEqual(TopicReadTracker.objects.filter(user=self.user).count(), 1)
        self.assertEqual(TopicReadTracker.objects.filter(user=self.user, topic=topic_1).count(), 1)

        # user reads topic_2, they should get a forum read tracker,
        #  there should be no topic read trackers for the user
        client.get(topic_2.get_absolute_url())
        self.assertEqual(TopicReadTracker.objects.all().count(), 0)
        self.assertEqual(ForumReadTracker.objects.all().count(), 1)
        self.assertEqual(ForumReadTracker.objects.filter(user=self.user).count(), 1)
        self.assertEqual(ForumReadTracker.objects.filter(user=self.user, forum=self.forum).count(), 1)

    def test_read_tracker_after_posting(self):
        client = Client()
        client.login(username='zeus', password='zeus')
        add_post_url = reverse('pybb:add_post', kwargs={'topic_id': self.topic.id})
        response = client.get(add_post_url)
        values = self.get_form_values(response)
        values['body'] = 'test tracking'
        response = client.post(add_post_url, values, follow=True)

        # after posting in topic it should be readed
        # because there is only one topic, so whole forum should be marked as readed
        self.assertEqual(TopicReadTracker.objects.filter(user=self.user, topic=self.topic).count(), 0)
        self.assertEqual(ForumReadTracker.objects.filter(user=self.user, forum=self.forum).count(), 1)

    def test_pybb_is_topic_unread_filter(self):
        forum_1 = self.forum
        topic_1 = self.topic
        topic_2 = Topic.objects.create(name='topic_2', forum=forum_1, user=self.user)

        forum_2 = Forum.objects.create(name='forum_2', description='forum2', category=self.category)
        topic_3 = Topic.objects.create(name='topic_2', forum=forum_2, user=self.user)

        Post(topic=topic_1, user=self.user, body='one').save()
        Post(topic=topic_2, user=self.user, body='two').save()
        Post(topic=topic_3, user=self.user, body='three').save()

        user_ann = User.objects.create_user('ann', 'ann@localhost', 'ann')
        client_ann = Client()
        client_ann.login(username='ann', password='ann')

        # Two topics, each with one post. everything is unread, so the db should reflect that:
        self.assertTrue(pybb_is_topic_unread(topic_1, user_ann))
        self.assertTrue(pybb_is_topic_unread(topic_2, user_ann))
        self.assertTrue(pybb_is_topic_unread(topic_3, user_ann))
        self.assertListEqual(
            [t.unread for t in pybb_topic_unread([topic_1, topic_2, topic_3], user_ann)],
            [True, True, True])

        client_ann.get(topic_1.get_absolute_url())
        topic_1 = Topic.objects.get(id=topic_1.id)
        topic_2 = Topic.objects.get(id=topic_2.id)
        topic_3 = Topic.objects.get(id=topic_3.id)
        self.assertFalse(pybb_is_topic_unread(topic_1, user_ann))
        self.assertTrue(pybb_is_topic_unread(topic_2, user_ann))
        self.assertTrue(pybb_is_topic_unread(topic_3, user_ann))
        self.assertListEqual(
            [t.unread for t in pybb_topic_unread([topic_1, topic_2, topic_3], user_ann)],
            [False, True, True])

        client_ann.get(topic_2.get_absolute_url())
        topic_1 = Topic.objects.get(id=topic_1.id)
        topic_2 = Topic.objects.get(id=topic_2.id)
        topic_3 = Topic.objects.get(id=topic_3.id)
        self.assertFalse(pybb_is_topic_unread(topic_1, user_ann))
        self.assertFalse(pybb_is_topic_unread(topic_2, user_ann))
        self.assertTrue(pybb_is_topic_unread(topic_3, user_ann))
        self.assertListEqual(
            [t.unread for t in pybb_topic_unread([topic_1, topic_2, topic_3], user_ann)],
            [False, False, True])

        client_ann.get(topic_3.get_absolute_url())
        topic_1 = Topic.objects.get(id=topic_1.id)
        topic_2 = Topic.objects.get(id=topic_2.id)
        topic_3 = Topic.objects.get(id=topic_3.id)
        self.assertFalse(pybb_is_topic_unread(topic_1, user_ann))
        self.assertFalse(pybb_is_topic_unread(topic_2, user_ann))
        self.assertFalse(pybb_is_topic_unread(topic_3, user_ann))
        self.assertListEqual(
            [t.unread for t in pybb_topic_unread([topic_1, topic_2, topic_3], user_ann)],
            [False, False, False])

    def test_is_forum_unread_filter(self):
        Forum.objects.all().delete()

        forum_parent = Forum.objects.create(name='f1', category=self.category)
        forum_child1 = Forum.objects.create(name='f2', category=self.category, parent=forum_parent)
        forum_child2 = Forum.objects.create(name='f3', category=self.category, parent=forum_parent)
        topic_1 = Topic.objects.create(name='topic_1', forum=forum_parent, user=self.user)
        topic_2 = Topic.objects.create(name='topic_2', forum=forum_child1, user=self.user)
        topic_3 = Topic.objects.create(name='topic_3', forum=forum_child2, user=self.user)

        Post(topic=topic_1, user=self.user, body='one').save()
        Post(topic=topic_2, user=self.user, body='two').save()
        Post(topic=topic_3, user=self.user, body='three').save()

        user_ann = User.objects.create_user('ann', 'ann@localhost', 'ann')
        client_ann = Client()
        client_ann.login(username='ann', password='ann')

        forum_parent = Forum.objects.get(id=forum_parent.id)
        forum_child1 = Forum.objects.get(id=forum_child1.id)
        forum_child2 = Forum.objects.get(id=forum_child2.id)
        self.assertListEqual([f.unread for f in pybb_forum_unread([forum_parent, forum_child1, forum_child2], user_ann)],
                             [True, True, True])

        # unless we read parent topic, there is unreaded topics in child forums
        client_ann.get(topic_1.get_absolute_url())
        forum_parent = Forum.objects.get(id=forum_parent.id)
        forum_child1 = Forum.objects.get(id=forum_child1.id)
        forum_child2 = Forum.objects.get(id=forum_child2.id)
        self.assertListEqual([f.unread for f in pybb_forum_unread([forum_parent, forum_child1, forum_child2], user_ann)],
                             [True, True, True])

        # still unreaded topic in one of the child forums
        client_ann.get(topic_2.get_absolute_url())
        forum_parent = Forum.objects.get(id=forum_parent.id)
        forum_child1 = Forum.objects.get(id=forum_child1.id)
        forum_child2 = Forum.objects.get(id=forum_child2.id)
        self.assertListEqual([f.unread for f in pybb_forum_unread([forum_parent, forum_child1, forum_child2], user_ann)],
                             [True, False, True])

        # all topics readed
        client_ann.get(topic_3.get_absolute_url())
        forum_parent = Forum.objects.get(id=forum_parent.id)
        forum_child1 = Forum.objects.get(id=forum_child1.id)
        forum_child2 = Forum.objects.get(id=forum_child2.id)
        self.assertListEqual([f.unread for f in pybb_forum_unread([forum_parent, forum_child1, forum_child2], user_ann)],
                             [False, False, False])

    @skipUnlessDBFeature('supports_microsecond_precision')
    def test_read_tracker_when_topics_forum_changed(self):
        forum_1 = Forum.objects.create(name='f1', description='bar', category=self.category)
        forum_2 = Forum.objects.create(name='f2', description='bar', category=self.category)
        topic_1 = Topic.objects.create(name='t1', forum=forum_1, user=self.user)
        topic_2 = Topic.objects.create(name='t2', forum=forum_2, user=self.user)

        Post.objects.create(topic=topic_1, user=self.user, body='one')
        Post.objects.create(topic=topic_2, user=self.user, body='two')

        user_ann = User.objects.create_user('ann', 'ann@localhost', 'ann')
        client_ann = Client()
        client_ann.login(username='ann', password='ann')

        # Everything is unread
        self.assertListEqual([t.unread for t in pybb_topic_unread([topic_1, topic_2], user_ann)], [True, True])
        self.assertListEqual([t.unread for t in pybb_forum_unread([forum_1, forum_2], user_ann)], [True, True])

        # read all
        client_ann.get(reverse('pybb:mark_all_as_read'))
        self.assertListEqual([t.unread for t in pybb_topic_unread([topic_1, topic_2], user_ann)], [False, False])
        self.assertListEqual([t.unread for t in pybb_forum_unread([forum_1, forum_2], user_ann)], [False, False])

        post = Post.objects.create(topic=topic_1, user=self.user, body='three')
        post = Post.objects.get(id=post.id)  # get post with timestamp from DB

        topic_1 = Topic.objects.get(id=topic_1.id)
        topic_2 = Topic.objects.get(id=topic_2.id)
        self.assertAlmostEqual(topic_1.updated, post.updated or post.created, delta=datetime.timedelta(milliseconds=50))
        self.assertAlmostEqual(forum_1.updated, post.updated or post.created, delta=datetime.timedelta(milliseconds=50))
        self.assertListEqual([t.unread for t in pybb_topic_unread([topic_1, topic_2], user_ann)], [True, False])
        self.assertListEqual([t.unread for t in pybb_forum_unread([forum_1, forum_2], user_ann)], [True, False])

        post.topic = topic_2
        post.save()
        topic_1 = Topic.objects.get(id=topic_1.id)
        topic_2 = Topic.objects.get(id=topic_2.id)
        forum_1 = Forum.objects.get(id=forum_1.id)
        forum_2 = Forum.objects.get(id=forum_2.id)
        self.assertAlmostEqual(topic_2.updated, post.updated or post.created, delta=datetime.timedelta(milliseconds=50))
        self.assertAlmostEqual(forum_2.updated, post.updated or post.created, delta=datetime.timedelta(milliseconds=50))
        self.assertListEqual([t.unread for t in pybb_topic_unread([topic_1, topic_2], user_ann)], [False, True])
        self.assertListEqual([t.unread for t in pybb_forum_unread([forum_1, forum_2], user_ann)], [False, True])

        topic_2.forum = forum_1
        topic_2.save()
        topic_1 = Topic.objects.get(id=topic_1.id)
        topic_2 = Topic.objects.get(id=topic_2.id)
        forum_1 = Forum.objects.get(id=forum_1.id)
        forum_2 = Forum.objects.get(id=forum_2.id)
        self.assertAlmostEqual(forum_1.updated, post.updated or post.created, delta=datetime.timedelta(milliseconds=50))
        self.assertListEqual([t.unread for t in pybb_topic_unread([topic_1, topic_2], user_ann)], [False, True])
        self.assertListEqual([t.unread for t in pybb_forum_unread([forum_1, forum_2], user_ann)], [True, False])

    @skipUnlessDBFeature('supports_microsecond_precision')
    def test_open_first_unread_post(self):
        forum_1 = self.forum
        topic_1 = Topic.objects.create(name='topic_1', forum=forum_1, user=self.user)
        topic_2 = Topic.objects.create(name='topic_2', forum=forum_1, user=self.user)

        post_1_1 = Post.objects.create(topic=topic_1, user=self.user, body='1_1')
        post_1_2 = Post.objects.create(topic=topic_1, user=self.user, body='1_2')
        post_2_1 = Post.objects.create(topic=topic_2, user=self.user, body='2_1')

        user_ann = User.objects.create_user('ann', 'ann@localhost', 'ann')
        client_ann = Client()
        client_ann.login(username='ann', password='ann')

        response = client_ann.get(topic_1.get_absolute_url(), data={'first-unread': 1}, follow=True)
        self.assertRedirects(response, '%s?page=%d#post-%d' % (topic_1.get_absolute_url(), 1, post_1_1.id))

        response = client_ann.get(topic_1.get_absolute_url(), data={'first-unread': 1}, follow=True)
        self.assertRedirects(response, '%s?page=%d#post-%d' % (topic_1.get_absolute_url(), 1, post_1_2.id))

        response = client_ann.get(topic_2.get_absolute_url(), data={'first-unread': 1}, follow=True)
        self.assertRedirects(response, '%s?page=%d#post-%d' % (topic_2.get_absolute_url(), 1, post_2_1.id))

        post_1_3 = Post.objects.create(topic=topic_1, user=self.user, body='1_3')
        post_1_4 = Post.objects.create(topic=topic_1, user=self.user, body='1_4')

        response = client_ann.get(topic_1.get_absolute_url(), data={'first-unread': 1}, follow=True)
        self.assertRedirects(response, '%s?page=%d#post-%d' % (topic_1.get_absolute_url(), 1, post_1_3.id))

    @skipUnlessDBFeature('supports_microsecond_precision')
    def test_latest_topics(self):

        category_2 = Category.objects.create(name='cat2')
        forum_2 = Forum.objects.create(name='forum_2', category=category_2)
        topic_3 = Topic.objects.create(name='topic_3', forum=forum_2, user=self.user)

        topic_2 = Topic.objects.create(name='topic_2', forum=self.forum, user=self.user)

        topic_1 = self.topic
        post = topic_1.posts.all()[0]
        post.body = 'Something completely different'
        post.save()

        self.login_client()
        response = self.client.get(reverse('pybb:topic_latest'))
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(list(response.context['topic_list']), [topic_1, topic_2, topic_3])

        topic_2.forum.hidden = True
        topic_2.forum.save()
        response = self.client.get(reverse('pybb:topic_latest'))
        self.assertListEqual(list(response.context['topic_list']), [topic_3])

        topic_2.forum.hidden = False
        topic_2.forum.save()
        category_2.hidden = True
        category_2.save()
        response = self.client.get(reverse('pybb:topic_latest'))
        self.assertListEqual(list(response.context['topic_list']), [topic_1, topic_2])

        topic_2.forum.hidden = False
        topic_2.forum.save()
        category_2.hidden = False
        category_2.save()
        topic_1.on_moderation = True
        topic_1.save()
        response = self.client.get(reverse('pybb:topic_latest'))
        self.assertListEqual(list(response.context['topic_list']), [topic_1, topic_2, topic_3])

        topic_1.user = User.objects.create_user('another', 'another@localhost', 'another')
        topic_1.save()
        response = self.client.get(reverse('pybb:topic_latest'))
        self.assertListEqual(list(response.context['topic_list']), [topic_2, topic_3])

        topic_1.forum.moderators.add(self.user)
        response = self.client.get(reverse('pybb:topic_latest'))
        self.assertListEqual(list(response.context['topic_list']), [topic_1, topic_2, topic_3])

        topic_1.forum.moderators.remove(self.user)
        self.user.is_superuser = True
        self.user.save()
        response = self.client.get(reverse('pybb:topic_latest'))
        self.assertListEqual(list(response.context['topic_list']), [topic_1, topic_2, topic_3])

        self.client.logout()
        response = self.client.get(reverse('pybb:topic_latest'))
        self.assertListEqual(list(response.context['topic_list']), [topic_2, topic_3])

    def test_hidden(self):
        client = Client()
        category = Category(name='hcat', hidden=True)
        category.save()
        forum_in_hidden = Forum(name='in_hidden', category=category)
        forum_in_hidden.save()
        topic_in_hidden = Topic(forum=forum_in_hidden, name='in_hidden', user=self.user)
        topic_in_hidden.save()

        forum_hidden = Forum(name='hidden', category=self.category, hidden=True)
        forum_hidden.save()
        topic_hidden = Topic(forum=forum_hidden, name='hidden', user=self.user)
        topic_hidden.save()

        post_hidden = Post(topic=topic_hidden, user=self.user, body='hidden')
        post_hidden.save()

        post_in_hidden = Post(topic=topic_in_hidden, user=self.user, body='hidden')
        post_in_hidden.save()

        self.assertFalse(category.id in [c.id for c in client.get(reverse('pybb:index')).context['categories']])
        self.assertEqual(client.get(category.get_absolute_url()).status_code, 302)
        self.assertEqual(client.get(forum_in_hidden.get_absolute_url()).status_code, 302)
        self.assertEqual(client.get(topic_in_hidden.get_absolute_url()).status_code, 302)

        self.assertNotContains(client.get(reverse('pybb:index')), forum_hidden.get_absolute_url())
        self.assertNotContains(client.get(reverse('pybb:feed_topics')), topic_hidden.get_absolute_url())
        self.assertNotContains(client.get(reverse('pybb:feed_topics')), topic_in_hidden.get_absolute_url())

        self.assertNotContains(client.get(reverse('pybb:feed_posts')), post_hidden.get_absolute_url())
        self.assertNotContains(client.get(reverse('pybb:feed_posts')), post_in_hidden.get_absolute_url())
        self.assertEqual(client.get(forum_hidden.get_absolute_url()).status_code, 302)
        self.assertEqual(client.get(topic_hidden.get_absolute_url()).status_code, 302)

        user = User.objects.create_user('someguy', 'email@abc.xyz', 'password')
        client.login(username='someguy', password='password')

        response = client.get(reverse('pybb:add_post', kwargs={'topic_id': self.topic.id}))
        self.assertEqual(response.status_code, 200, response)

        response = client.get(reverse('pybb:add_post', kwargs={'topic_id': self.topic.id}), data={'quote_id': post_hidden.id})
        self.assertEqual(response.status_code, 403, response)

        client.login(username='zeus', password='zeus')
        self.assertFalse(category.id in [c.id for c in client.get(reverse('pybb:index')).context['categories']])
        self.assertNotContains(client.get(reverse('pybb:index')), forum_hidden.get_absolute_url())
        self.assertEqual(client.get(category.get_absolute_url()).status_code, 403)
        self.assertEqual(client.get(forum_in_hidden.get_absolute_url()).status_code, 403)
        self.assertEqual(client.get(topic_in_hidden.get_absolute_url()).status_code, 403)
        self.assertEqual(client.get(forum_hidden.get_absolute_url()).status_code, 403)
        self.assertEqual(client.get(topic_hidden.get_absolute_url()).status_code, 403)

        self.user.is_staff = True
        self.user.save()
        self.assertTrue(category.id in [c.id for c in client.get(reverse('pybb:index')).context['categories']])
        self.assertContains(client.get(reverse('pybb:index')), forum_hidden.get_absolute_url())
        self.assertEqual(client.get(category.get_absolute_url()).status_code, 200)
        self.assertEqual(client.get(forum_in_hidden.get_absolute_url()).status_code, 200)
        self.assertEqual(client.get(topic_in_hidden.get_absolute_url()).status_code, 200)
        self.assertEqual(client.get(forum_hidden.get_absolute_url()).status_code, 200)
        self.assertEqual(client.get(topic_hidden.get_absolute_url()).status_code, 200)


    def test_inactive(self):
        self.login_client()
        url = reverse('pybb:add_post', kwargs={'topic_id': self.topic.id})
        response = self.client.get(url)
        values = self.get_form_values(response)
        values['body'] = 'test ban'
        response = self.client.post(url, values, follow=True)
        self.assertEqual(len(Post.objects.filter(body='test ban')), 1)
        self.user.is_active = False
        self.user.save()
        values['body'] = 'test ban 2'
        self.client.post(url, values, follow=True)
        self.assertEqual(len(Post.objects.filter(body='test ban 2')), 0)

    def get_csrf(self, form):
        return form.xpath('//input[@name="csrfmiddlewaretoken"]/@value')[0]

    def test_user_blocking(self):
        user = User.objects.create_user('test', 'test@localhost', 'test')
        topic = Topic.objects.create(name='topic', forum=self.forum, user=user)
        p1 = Post.objects.create(topic=topic, user=user, body='bbcode [b]test[/b]')
        p2 = Post.objects.create(topic=topic, user=user, body='bbcode [b]test[/b]')
        self.user.is_superuser = True
        self.user.save()
        self.login_client()
        response = self.client.get(reverse('pybb:block_user', args=[user.username]), follow=True)
        self.assertEqual(response.status_code, 405)
        response = self.client.post(reverse('pybb:block_user', args=[user.username]), follow=True)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username=user.username)
        self.assertFalse(user.is_active)
        self.assertEqual(Topic.objects.filter().count(), 2)
        self.assertEqual(Post.objects.filter(user=user).count(), 2)

        user.is_active = True
        user.save()
        self.assertEqual(Topic.objects.count(), 2)
        response = self.client.post(reverse('pybb:block_user', args=[user.username]),
                                    data={'block_and_delete_messages': 'block_and_delete_messages'}, follow=True)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username=user.username)
        self.assertFalse(user.is_active)
        self.assertEqual(Topic.objects.count(), 1)
        self.assertEqual(Post.objects.filter(user=user).count(), 0)

    def test_user_unblocking(self):
        user = User.objects.create_user('test', 'test@localhost', 'test')
        user.is_active=False
        user.save()
        self.user.is_superuser = True
        self.user.save()
        self.login_client()
        response = self.client.get(reverse('pybb:unblock_user', args=[user.username]), follow=True)
        self.assertEqual(response.status_code, 405)
        response = self.client.post(reverse('pybb:unblock_user', args=[user.username]), follow=True)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username=user.username)
        self.assertTrue(user.is_active)

    def test_ajax_preview(self):
        self.login_client()
        response = self.client.post(reverse('pybb:post_ajax_preview'), data={'data': '[b]test bbcode ajax preview[/b]'})
        self.assertContains(response, '<strong>test bbcode ajax preview</strong>')

    def test_headline(self):
        self.forum.headline = 'test <b>headline</b>'
        self.forum.save()
        client = Client()
        self.assertContains(client.get(self.forum.get_absolute_url()), 'test <b>headline</b>')

    def test_quote(self):
        self.login_client()
        response = self.client.get(reverse('pybb:add_post', kwargs={'topic_id': self.topic.id}),
                                   data={'quote_id': self.post.id, 'body': 'test tracking'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.post.body)

    def test_edit_post(self):
        self.login_client()
        edit_post_url = reverse('pybb:edit_post', kwargs={'pk': self.post.id})
        response = self.client.get(edit_post_url)
        self.assertEqual(response.status_code, 200)
        tree = html.fromstring(response.content)
        values = dict(tree.xpath('//form[@method="post"]')[0].form_values())
        values['body'] = 'test edit'
        response = self.client.post(edit_post_url, data=values, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.get(pk=self.post.id).body, 'test edit')
        response = self.client.get(self.post.get_absolute_url(), follow=True)
        self.assertContains(response, 'test edit')
        self.assertIsNotNone(Post.objects.get(id=self.post.id).updated)

    def test_stick(self):
        self.user.is_superuser = True
        self.user.save()
        self.login_client()
        self.assertEqual(
            self.client.get(reverse('pybb:stick_topic', kwargs={'pk': self.topic.id}), follow=True).status_code, 200)
        self.assertEqual(
            self.client.get(reverse('pybb:unstick_topic', kwargs={'pk': self.topic.id}), follow=True).status_code, 200)

    def test_delete_view(self):
        post = Post(topic=self.topic, user=self.user, body='test to delete')
        post.save()
        self.user.is_superuser = True
        self.user.save()
        self.login_client()
        response = self.client.post(reverse('pybb:delete_post', args=[post.id]), follow=True)
        self.assertEqual(response.status_code, 200)
        # Check that topic and forum exists ;)
        self.assertEqual(Topic.objects.filter(id=self.topic.id).count(), 1)
        self.assertEqual(Forum.objects.filter(id=self.forum.id).count(), 1)

        # Delete topic
        response = self.client.post(reverse('pybb:delete_post', args=[self.post.id]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.filter(id=self.post.id).count(), 0)
        self.assertEqual(Topic.objects.filter(id=self.topic.id).count(), 0)
        self.assertEqual(Forum.objects.filter(id=self.forum.id).count(), 1)

    def test_open_close(self):
        self.user.is_superuser = True
        self.user.save()
        self.login_client()
        add_post_url = reverse('pybb:add_post', args=[self.topic.id])
        response = self.client.get(add_post_url)
        values = self.get_form_values(response)
        values['body'] = 'test closed'
        response = self.client.get(reverse('pybb:close_topic', args=[self.topic.id]), follow=True)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(add_post_url, values, follow=True)
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse('pybb:open_topic', args=[self.topic.id]), follow=True)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(add_post_url, values, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_subscription(self):
        user2 = User.objects.create_user(username='user2', password='user2', email='user2@someserver.com')
        user3 = User.objects.create_user(username='user3', password='user3', email='user3@example.com')
        client = Client()

        client.login(username='user2', password='user2')
        subscribe_url = reverse('pybb:add_subscription', args=[self.topic.id])
        response = client.get(self.topic.get_absolute_url())
        subscribe_links = html.fromstring(response.content).xpath('//a[@href="%s"]' % subscribe_url)
        self.assertEqual(len(subscribe_links), 1)

        response = client.get(subscribe_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(user2, self.topic.subscribers.all())

        self.topic.subscribers.add(user3)

        # create a new reply (with another user)
        self.client.login(username='zeus', password='zeus')
        add_post_url = reverse('pybb:add_post', args=[self.topic.id])
        response = self.client.get(add_post_url)
        values = self.get_form_values(response)
        values['body'] = 'test subscribtion юникод'
        response = self.client.post(add_post_url, values, follow=True)
        self.assertEqual(response.status_code, 200)
        new_post = Post.objects.order_by('-id')[0]

        # there should only be one email in the outbox (to user2) because @example.com are ignored
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], user2.email)
        self.assertTrue([msg for msg in mail.outbox if new_post.get_absolute_url() in msg.body])

        # unsubscribe
        client.login(username='user2', password='user2')
        self.assertTrue([msg for msg in mail.outbox if new_post.get_absolute_url() in msg.body])
        response = client.get(reverse('pybb:delete_subscription', args=[self.topic.id]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(user2, self.topic.subscribers.all())

    def test_subscription_disabled(self):
        orig_conf = pybb_settings.PYBB_DISABLE_SUBSCRIPTIONS
        pybb_settings.PYBB_DISABLE_SUBSCRIPTIONS = True

        user2 = User.objects.create_user(username='user2', password='user2', email='user2@someserver.com')
        user3 = User.objects.create_user(username='user3', password='user3', email='user3@someserver.com')
        client = Client()

        client.login(username='user2', password='user2')
        subscribe_url = reverse('pybb:add_subscription', args=[self.topic.id])
        response = client.get(self.topic.get_absolute_url())
        subscribe_links = html.fromstring(response.content).xpath('//a[@href="%s"]' % subscribe_url)
        self.assertEqual(len(subscribe_links), 0)

        response = client.get(subscribe_url, follow=True)
        self.assertEqual(response.status_code, 403)

        self.topic.subscribers.add(user3)

        # create a new reply (with another user)
        self.client.login(username='zeus', password='zeus')
        add_post_url = reverse('pybb:add_post', args=[self.topic.id])
        response = self.client.get(add_post_url)
        values = self.get_form_values(response)
        values['body'] = 'test subscribtion юникод'
        response = self.client.post(add_post_url, values, follow=True)
        self.assertEqual(response.status_code, 200)
        new_post = Post.objects.order_by('-id')[0]

        # there should be one email in the outbox (user3)
        #because already subscribed users will still receive notifications.
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], user3.email)

        pybb_settings.PYBB_DISABLE_SUBSCRIPTIONS = orig_conf

    def test_notifications_disabled(self):
        orig_conf = pybb_settings.PYBB_DISABLE_NOTIFICATIONS
        pybb_settings.PYBB_DISABLE_NOTIFICATIONS = True

        user2 = User.objects.create_user(username='user2', password='user2', email='user2@someserver.com')
        user3 = User.objects.create_user(username='user3', password='user3', email='user3@someserver.com')
        client = Client()

        client.login(username='user2', password='user2')
        subscribe_url = reverse('pybb:add_subscription', args=[self.topic.id])
        response = client.get(self.topic.get_absolute_url())
        subscribe_links = html.fromstring(response.content).xpath('//a[@href="%s"]' % subscribe_url)
        self.assertEqual(len(subscribe_links), 1)
        response = client.get(subscribe_url, follow=True)
        self.assertEqual(response.status_code, 200)

        self.topic.subscribers.add(user3)

        # create a new reply (with another user)
        self.client.login(username='zeus', password='zeus')
        add_post_url = reverse('pybb:add_post', args=[self.topic.id])
        response = self.client.get(add_post_url)
        values = self.get_form_values(response)
        values['body'] = 'test subscribtion юникод'
        response = self.client.post(add_post_url, values, follow=True)
        self.assertEqual(response.status_code, 200)
        new_post = Post.objects.order_by('-id')[0]

        # there should be no email in the outbox
        self.assertEqual(len(mail.outbox), 0)

        pybb_settings.PYBB_DISABLE_NOTIFICATIONS = orig_conf

    @skipUnlessDBFeature('supports_microsecond_precision')
    def test_topic_updated(self):
        topic = Topic(name='new topic', forum=self.forum, user=self.user)
        topic.save()
        post = Post(topic=topic, user=self.user, body='bbcode [b]test[/b]')
        post.save()
        client = Client()
        response = client.get(self.forum.get_absolute_url())
        self.assertEqual(response.context['topic_list'][0], topic)
        post = Post(topic=self.topic, user=self.user, body='bbcode [b]test[/b]')
        post.save()
        client = Client()
        response = client.get(self.forum.get_absolute_url())
        self.assertEqual(response.context['topic_list'][0], self.topic)

    def test_topic_deleted(self):
        forum_1 = Forum.objects.create(name='new forum', category=self.category)
        topic_1 = Topic.objects.create(name='new topic', forum=forum_1, user=self.user)
        post_1 = Post.objects.create(topic=topic_1, user=self.user, body='test')
        post_1 = Post.objects.get(id=post_1.id)

        self.assertAlmostEqual(topic_1.updated, post_1.created, delta=datetime.timedelta(milliseconds=50))
        self.assertAlmostEqual(forum_1.updated, post_1.created, delta=datetime.timedelta(milliseconds=50))

        topic_2 = Topic.objects.create(name='another topic', forum=forum_1, user=self.user)
        post_2 = Post.objects.create(topic=topic_2, user=self.user, body='another test')
        post_2 = Post.objects.get(id=post_2.id)

        self.assertAlmostEqual(topic_2.updated, post_2.created, delta=datetime.timedelta(milliseconds=50))
        self.assertAlmostEqual(forum_1.updated, post_2.created, delta=datetime.timedelta(milliseconds=50))

        topic_2.delete()
        forum_1 = Forum.objects.get(id=forum_1.id)
        self.assertAlmostEqual(forum_1.updated, post_1.created, delta=datetime.timedelta(milliseconds=50))
        self.assertEqual(forum_1.topics.count(), 1)
        self.assertEqual(forum_1.posts.count(), 1)

        post_1.delete()
        forum_1 = Forum.objects.get(id=forum_1.id)
        self.assertEqual(forum_1.topics.count(), 0)
        self.assertEqual(forum_1.posts.count(), 0)

    def test_user_views(self):
        response = self.client.get(reverse('pybb:user', kwargs={'username': self.user.username}))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('pybb:user_posts', kwargs={'username': self.user.username}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object_list'].count(), 1)

        response = self.client.get(reverse('pybb:user_topics', kwargs={'username': self.user.username}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object_list'].count(), 1)

        self.topic.forum.hidden = True
        self.topic.forum.save()

        self.client.logout()

        response = self.client.get(reverse('pybb:user_posts', kwargs={'username': self.user.username}))
        self.assertEqual(response.context['object_list'].count(), 0)

        response = self.client.get(reverse('pybb:user_topics', kwargs={'username': self.user.username}))
        self.assertEqual(response.context['object_list'].count(), 0)

    def test_post_count(self):
        topic = Topic(name='etopic', forum=self.forum, user=self.user)
        topic.save()
        post = Post(topic=topic, user=self.user, body='test') # another post
        post.save()
        self.assertEqual(util.get_pybb_profile(self.user).user.posts.count(), 2)
        post.body = 'test2'
        post.save()
        self.assertEqual(Profile.objects.get(pk=util.get_pybb_profile(self.user).pk).user.posts.count(), 2)
        post.delete()
        self.assertEqual(Profile.objects.get(pk=util.get_pybb_profile(self.user).pk).user.posts.count(), 1)

    def test_latest_topics_tag(self):
        Topic.objects.all().delete()
        for i in range(10):
            Topic.objects.create(name='topic%s' % i, user=self.user, forum=self.forum)
        latest_topics = pybb_get_latest_topics(context=None, user=self.user)
        self.assertEqual(len(latest_topics), 5)
        self.assertEqual(latest_topics[0].name, 'topic9')
        self.assertEqual(latest_topics[4].name, 'topic5')

    def test_latest_posts_tag(self):
        Post.objects.all().delete()
        for i in range(10):
            Post.objects.create(body='post%s' % i, user=self.user, topic=self.topic)
        latest_topics = pybb_get_latest_posts(context=None, user=self.user)
        self.assertEqual(len(latest_topics), 5)
        self.assertEqual(latest_topics[0].body, 'post9')
        self.assertEqual(latest_topics[4].body, 'post5')

    def test_multiple_objects_returned(self):
        """
        see issue #87: https://github.com/hovel/pybbm/issues/87
        """
        self.assertFalse(self.user.is_superuser)
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.topic.on_moderation)
        self.assertEqual(self.topic.user, self.user)
        user1 = User.objects.create_user('geyser', 'geyser@localhost', 'geyser')
        self.topic.forum.moderators.add(self.user)
        self.topic.forum.moderators.add(user1)

        self.login_client()
        response = self.client.get(reverse('pybb:add_post', kwargs={'topic_id': self.topic.id}))
        self.assertEqual(response.status_code, 200)

    def tearDown(self):
        pybb_settings.PYBB_ENABLE_ANONYMOUS_POST = self.ORIG_PYBB_ENABLE_ANONYMOUS_POST
        pybb_settings.PYBB_PREMODERATION = self.ORIG_PYBB_PREMODERATION
