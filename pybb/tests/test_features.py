# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime
from pydash import py_

from django.conf import settings
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import skipUnlessDBFeature, Client, override_settings
from lxml import html
from rest_framework.test import APITestCase, APIClient

from pybb import util
from pybb.models import Forum, Topic, Post, TopicReadTracker, ForumReadTracker, Category
from pybb.settings import settings as pybb_settings
from pybb.templatetags.pybb_tags import pybb_topic_unread, pybb_is_topic_unread, pybb_forum_unread, \
    pybb_get_latest_topics, pybb_get_latest_posts
from pybb.tests.utils import Profile, User


@override_settings(PYBB_ENABLE_ANONYMOUS_POST=False, PYBB_PREMODERATION=False)
class FeaturesTest(APITestCase):

    def setUp(self):
        mail.outbox = []

    def test_base(self):
        # Check index page
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(name='xfoo', description='bar', category=category)
        Forum.objects.create(name='xfoo1', description='bar1', category=category, parent=forum)
        url = reverse('pybb:index')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'foo')
        self.assertEqual(len(response.data[0]['forums']), 2)

    def test_forum_page(self):
        # Check forum page
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(name='xfoo', description='bar', category=category)
        response = self.client.get(forum.get_absolute_url())
        self.assertEqual(response.data['name'], forum.name)

    def test_category_page(self):
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(name='xfoo', description='bar', category=category)
        Forum.objects.create(name='xfoo1', description='bar1', category=category, parent=forum)
        response = self.client.get(category.get_absolute_url())
        self.assertEqual(response.status_code, 200)

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
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(name='xfoo', description='bar', category=category)
        topic = Topic.objects.create(name='etopic', forum=forum, user=user)
        post = Post(topic=topic, user=user, body='bbcode [b]test[/b]')
        post.save()
        post.delete()
        Topic.objects.get(id=topic.id)
        Forum.objects.get(id=forum.id)

    def test_topic_deletion(self):
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(name='xfoo', description='bar', category=category)
        topic = Topic(name='xtopic', forum=forum, user=user)
        topic.save()
        post = Post(topic=topic, user=user, body='one')
        post.save()
        post = Post(topic=topic, user=user, body='two')
        post.save()
        post.delete()
        Topic.objects.get(id=topic.id)
        Forum.objects.get(id=forum.id)
        topic.delete()
        Forum.objects.get(id=forum.id)

    def test_forum_updated(self):
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(name='xfoo', description='bar', category=category)
        topic = Topic(name='xtopic', forum=forum, user=user)
        topic.save()
        post = Post(topic=topic, user=user, body='one')
        post.save()
        post = Post.objects.get(id=post.id)
        self.assertAlmostEqual(forum.updated, post.created, delta=datetime.timedelta(milliseconds=50))

    @skipUnlessDBFeature('supports_microsecond_precision')
    def test_read_tracking(self):
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(name='xfoo', description='bar', category=category)
        topic = Topic(name='xtopic', forum=forum, user=user)
        topic.save()
        post = Post(topic=topic, user=user, body='one')
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
        post = Post(topic=topic, user=user, body='one')
        post.save()
        client.get(reverse('pybb:mark_all_as_read'))
        tree = html.fromstring(client.get(reverse('pybb:index')).content)
        self.assertFalse(
            tree.xpath('//a[@href="%s"]/parent::td[contains(@class,"unread")]' % topic.forum.get_absolute_url()))
        # Empty forum - readed
        f = Forum(name='empty', category=category)
        f.save()
        tree = html.fromstring(client.get(reverse('pybb:index')).content)
        self.assertFalse(tree.xpath('//a[@href="%s"]/parent::td[contains(@class,"unread")]' % f.get_absolute_url()))

    @skipUnlessDBFeature('supports_microsecond_precision')
    def test_read_tracking_multi_user(self):
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(name='xfoo', description='bar', category=category)
        topic_1 = Topic(name='xtopic', forum=forum, user=user)
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
        add_topic_url = reverse('pybb:add_topic', kwargs={'forum_id': forum.id})
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
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(name='xfoo', description='bar', category=category)
        topic_1 = Topic.objects.create(name='xtopic', forum=forum, user=user)
        topic_2 = Topic.objects.create(name='topic_2', forum=forum, user=user)

        Post(topic=topic_2, user=user, body='one').save()

        forum_2 = Forum(name='forum_2', description='bar', category=self.category)
        forum_2.save()

        Topic(name='garbage', forum=forum_2, user=user).save()

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
        self.assertEqual(ForumReadTracker.objects.filter(user=user).count(), 1)
        self.assertEqual(ForumReadTracker.objects.filter(user=user, forum=forum).count(), 1)

    def test_read_tracker_after_posting(self):
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(name='xfoo', description='bar', category=category)
        topic = Topic.objects.create(name='xtopic', forum=forum, user=user)
        client = Client()
        client.login(username='zeus', password='zeus')
        add_post_url = reverse('pybb:add_post', kwargs={'topic_id': topic.id})
        response = client.get(add_post_url)
        values = self.get_form_values(response)
        values['body'] = 'test tracking'
        response = client.post(add_post_url, values, follow=True)

        # after posting in topic it should be readed
        # because there is only one topic, so whole forum should be marked as readed
        self.assertEqual(TopicReadTracker.objects.filter(user=user, topic=topic).count(), 0)
        self.assertEqual(ForumReadTracker.objects.filter(user=user, forum=forum).count(), 1)

    def test_pybb_is_topic_unread_filter(self):
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(name='xfoo', description='bar', category=category)
        topic_1 = Topic.objects.create(name='xtopic', forum=forum, user=user)
        topic_2 = Topic.objects.create(name='topic_2', forum=forum, user=user)

        forum_2 = Forum.objects.create(name='forum_2', description='forum2', category=category)
        topic_3 = Topic.objects.create(name='topic_2', forum=forum_2, user=user)

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
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')

        forum_parent = Forum.objects.create(name='f1', category=category)
        forum_child1 = Forum.objects.create(name='f2', category=category, parent=forum_parent)
        forum_child2 = Forum.objects.create(name='f3', category=category, parent=forum_parent)
        topic_1 = Topic.objects.create(name='topic_1', forum=forum_parent, user=user)
        topic_2 = Topic.objects.create(name='topic_2', forum=forum_child1, user=user)
        topic_3 = Topic.objects.create(name='topic_3', forum=forum_child2, user=user)

        Post(topic=topic_1, user=user, body='one').save()
        Post(topic=topic_2, user=user, body='two').save()
        Post(topic=topic_3, user=user, body='three').save()

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
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum_1 = Forum.objects.create(name='f1', description='bar', category=category)
        forum_2 = Forum.objects.create(name='f2', description='bar', category=category)
        topic_1 = Topic.objects.create(name='t1', forum=forum_1, user=user)
        topic_2 = Topic.objects.create(name='t2', forum=forum_2, user=user)

        Post.objects.create(topic=topic_1, user=user, body='one')
        Post.objects.create(topic=topic_2, user=user, body='two')

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

        post = Post.objects.create(topic=topic_1, user=user, body='three')
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
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum_1 = Forum.objects.create(category=category, name='foo')
        topic_1 = Topic.objects.create(name='topic_1', forum=forum_1, user=user)
        topic_2 = Topic.objects.create(name='topic_2', forum=forum_1, user=user)

        post_1_1 = Post.objects.create(topic=topic_1, user=user, body='1_1')
        post_1_2 = Post.objects.create(topic=topic_1, user=user, body='1_2')
        post_2_1 = Post.objects.create(topic=topic_2, user=user, body='2_1')

        user_ann = User.objects.create_user('ann', 'ann@localhost', 'ann')
        client_ann = Client()
        client_ann.login(username='ann', password='ann')

        response = client_ann.get(topic_1.get_absolute_url(), data={'first-unread': 1}, follow=True)
        self.assertRedirects(response, '%s?page=%d#post-%d' % (topic_1.get_absolute_url(), 1, post_1_1.id))

        response = client_ann.get(topic_1.get_absolute_url(), data={'first-unread': 1}, follow=True)
        self.assertRedirects(response, '%s?page=%d#post-%d' % (topic_1.get_absolute_url(), 1, post_1_2.id))

        response = client_ann.get(topic_2.get_absolute_url(), data={'first-unread': 1}, follow=True)
        self.assertRedirects(response, '%s?page=%d#post-%d' % (topic_2.get_absolute_url(), 1, post_2_1.id))

        post_1_3 = Post.objects.create(topic=topic_1, user=user, body='1_3')
        post_1_4 = Post.objects.create(topic=topic_1, user=user, body='1_4')

        response = client_ann.get(topic_1.get_absolute_url(), data={'first-unread': 1}, follow=True)
        self.assertRedirects(response, '%s?page=%d#post-%d' % (topic_1.get_absolute_url(), 1, post_1_3.id))

    @skipUnlessDBFeature('supports_microsecond_precision')
    def test_latest_topics(self):
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(category=category, name='foo')
        category_2 = Category.objects.create(name='cat2')
        forum_2 = Forum.objects.create(name='forum_2', category=category_2)
        topic_1 = Topic.objects.create(name='topic_1', forum=forum, user=user)
        topic_3 = Topic.objects.create(name='topic_3', forum=forum_2, user=user)

        topic_2 = Topic.objects.create(name='topic_2', forum=forum, user=user)

        Post.objects.create(topic=topic_1, user=user, body='Something completely different')
        topic_list_url = reverse('pybb:topic_list')

        self.client.force_authenticate(user)
        response = self.client.get(topic_list_url)
        self.assertEqual(response.status_code, 200)
        id_list = py_(response.data['results']).pluck('id').value()
        self.assertListEqual(id_list, [topic_1.id, topic_2.id, topic_3.id])

        topic_2.forum.hidden = True
        topic_2.forum.save()
        response = self.client.get(topic_list_url)
        id_list = py_(response.data['results']).pluck('id').value()
        self.assertListEqual(id_list, [topic_3.id])

        topic_2.forum.hidden = False
        topic_2.forum.save()
        category_2.hidden = True
        category_2.save()
        response = self.client.get(topic_list_url)
        id_list = py_(response.data['results']).pluck('id').value()
        self.assertListEqual(id_list, [topic_1.id, topic_2.id])

        topic_2.forum.hidden = False
        topic_2.forum.save()
        category_2.hidden = False
        category_2.save()
        topic_1.on_moderation = True
        topic_1.save()
        response = self.client.get(topic_list_url)
        id_list = py_(response.data['results']).pluck('id').value()
        self.assertListEqual(id_list, [topic_1.id, topic_2.id, topic_3.id])

        topic_1.user = User.objects.create_user('another', 'another@localhost', 'another')
        topic_1.save()
        response = self.client.get(topic_list_url)
        id_list = py_(response.data['results']).pluck('id').value()
        self.assertListEqual(id_list, [topic_2.id, topic_3.id])

        topic_1.forum.moderators.add(user)
        response = self.client.get(topic_list_url)
        id_list = py_(response.data['results']).pluck('id').value()
        self.assertListEqual(id_list, [topic_1.id, topic_2.id, topic_3.id])

        topic_1.forum.moderators.remove(user)
        user.is_superuser = True
        user.save()
        response = self.client.get(topic_list_url)
        id_list = py_(response.data['results']).pluck('id').value()
        self.assertListEqual(id_list, [topic_1.id, topic_2.id, topic_3.id])

        self.client.logout()
        response = self.client.get(topic_list_url)
        id_list = py_(response.data['results']).pluck('id').value()
        self.assertListEqual(id_list, [topic_2.id, topic_3.id])

    def test_inactive(self):
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(category=category, name='foo')
        topic = Topic.objects.create(name='topic_1', forum=forum, user=user)
        self.client.force_authenticate(user)
        url = reverse('pybb:add_post')
        data = {
            'body': 'test ban',
            'topic': topic.id
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Post.objects.filter(body='test ban').exists())
        inactive_user = User.objects.create_user('inactive_user')
        inactive_user.is_active = False
        inactive_user.save()
        data['body'] = 'test ban 2'
        self.client.force_authenticate(inactive_user)
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Post.objects.filter(body='test ban 2').exists())

    def test_user_blocking(self):
        superuser = User.objects.create_superuser('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(category=category, name='foo')
        user = User.objects.create_user('test', 'test@localhost', 'test')
        topic = Topic.objects.create(name='topic', forum=forum, user=user)
        p1 = Post.objects.create(topic=topic, user=user, body='bbcode [b]test[/b]')
        p2 = Post.objects.create(topic=topic, user=user, body='bbcode [b]test[/b]')
        self.client.force_authenticate(superuser)
        response = self.client.get(reverse('pybb:block_user', args=[user.username]), follow=True)
        self.assertEqual(response.status_code, 405)
        response = self.client.post(reverse('pybb:block_user', args=[user.username]), follow=True)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username=user.username)
        self.assertFalse(user.is_active)
        self.assertEqual(Topic.objects.count(), 1)
        self.assertEqual(Post.objects.filter(user=user).count(), 2)

        user.is_active = True
        user.save()
        response = self.client.post(reverse('pybb:block_user', args=[user.username]),
                                    data={'block_and_delete_messages': True}, follow=True)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username=user.username)
        self.assertFalse(user.is_active)
        self.assertEqual(Topic.objects.count(), 0)
        self.assertEqual(Post.objects.filter(user=user).count(), 0)

    def test_user_unblocking(self):
        superuser = User.objects.create_superuser('zeus', 'zeus@localhost', 'zeus')
        user = User.objects.create_user('test', 'test@localhost', 'test')
        user.is_active = False
        user.save()
        self.client.force_authenticate(superuser)
        response = self.client.get(reverse('pybb:unblock_user', args=[user.username]), follow=True)
        self.assertEqual(response.status_code, 405)
        response = self.client.post(reverse('pybb:unblock_user', args=[user.username]), follow=True)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username=user.username)
        self.assertTrue(user.is_active)

    def test_ajax_preview(self):
        post_data = {
            'markup': 'bbcode',
            'message': '[b]test bbcode ajax preview[/b]'
        }
        response = self.client.post(reverse('pybb:preview_post'), data=post_data)
        self.assertEqual(response.data['markup'], 'bbcode')
        self.assertEqual(response.data['html'], '<strong>test bbcode ajax preview</strong>')

    def test_headline(self):
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(category=category, name='foo')
        forum.headline = 'test <b>headline</b>'
        forum.save()
        client = Client()
        self.assertContains(client.get(forum.get_absolute_url()), 'test <b>headline</b>')

    def test_quote(self):
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(category=category, name='foo')
        topic = Topic.objects.create(name='topic', forum=forum, user=user)
        post = Post.objects.create(topic=topic, user=user, body='bbcode [b]test[/b]')
        self.client.force_authenticate(user)
        response = self.client.get(reverse('pybb:add_post', kwargs={'topic_id': topic.id}),
                                   data={'quote_id': post.id, 'body': 'test tracking'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, post.body)

    def test_edit_post(self):
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(category=category, name='foo')
        topic = Topic.objects.create(name='topic', forum=forum, user=user)
        post = Post.objects.create(topic=topic, user=user, body='bbcode [b]test[/b]')
        self.client.force_authenticate(user)
        edit_post_url = reverse('pybb:edit_post', kwargs={'pk': post.id})
        values = {
            'body': 'test edit',
            'topic': topic.id
        }
        response = self.client.put(edit_post_url, data=values, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.get(pk=post.id).body, 'test edit')
        response = self.client.get(post.get_absolute_url(), follow=True)
        self.assertEqual(response.data['body'], 'test edit')
        self.assertIsNotNone(Post.objects.get(id=post.id).updated)

    def test_stick(self):
        superuser = User.objects.create_superuser('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(category=category, name='foo')
        topic = Topic.objects.create(name='topic', forum=forum, user=superuser)
        self.client.force_authenticate(superuser)
        self.assertEqual(
            self.client.get(reverse('pybb:stick_topic', kwargs={'pk': topic.id}), follow=True).status_code, 200)
        self.assertEqual(
            self.client.get(reverse('pybb:unstick_topic', kwargs={'pk': topic.id}), follow=True).status_code, 200)

    def test_delete_view(self):
        superuser = User.objects.create_superuser('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(category=category, name='foo')
        topic = Topic.objects.create(name='topic', forum=forum, user=superuser)
        topic_head = Post.objects.create(topic=topic, user=superuser, body='test topic head')
        post = Post.objects.create(topic=topic, user=superuser, body='test to delete')
        self.client.force_authenticate(superuser)
        response = self.client.delete(reverse('pybb:delete_post', args=[post.id]), follow=True)
        self.assertEqual(response.status_code, 204)
        # Check that topic and forum exists ;)
        self.assertEqual(Topic.objects.filter(id=topic.id).count(), 1)
        self.assertEqual(Forum.objects.filter(id=forum.id).count(), 1)

        # Delete topic
        response = self.client.delete(reverse('pybb:delete_post', args=[topic_head.id]), follow=True)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Post.objects.filter(id=post.id).count(), 0)
        self.assertEqual(Topic.objects.filter(id=topic.id).count(), 0)
        self.assertEqual(Forum.objects.filter(id=forum.id).count(), 1)

    def test_open_close(self):
        superuser = User.objects.create_superuser('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(category=category, name='foo')
        topic = Topic.objects.create(name='topic', forum=forum, user=superuser)
        self.client.force_authenticate(superuser)
        response = self.client.get(reverse('pybb:close_topic', args=[topic.id]), follow=True)
        use_post_request_msg = 'Should use a post request to make changes on the server'
        self.assertEqual(response.status_code, 405, use_post_request_msg)

        response = self.client.post(reverse('pybb:close_topic', args=[topic.id]), follow=True)
        self.assertEqual(response.status_code, 200)

        add_post_url = reverse('pybb:add_post')
        values = {'body': 'test closed', 'topic': topic.id}
        response = self.client.post(add_post_url, values, follow=True)
        self.assertEqual(response.status_code, 201, 'Superusers can post in closed topics')

        peon = User.objects.create_user('regular_user')
        self.client.force_authenticate(peon)
        response = self.client.post(add_post_url, values, follow=True)
        self.assertEqual(response.status_code, 403)

        self.client.force_authenticate(superuser)
        response = self.client.get(reverse('pybb:open_topic', args=[topic.id]), follow=True)
        self.assertEqual(response.status_code, 405, use_post_request_msg)
        response = self.client.post(reverse('pybb:open_topic', args=[topic.id]), follow=True)
        self.assertEqual(response.status_code, 200)

        self.client.force_authenticate(peon)
        response = self.client.post(add_post_url, values, follow=True)
        self.assertEqual(response.status_code, 201)

    def test_subscription(self):
        superuser = User.objects.create_superuser('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(category=category, name='foo')
        topic = Topic.objects.create(name='topic', forum=forum, user=superuser)
        user2 = User.objects.create_user(username='user2', password='user2', email='user2@someserver.com')
        user3 = User.objects.create_user(username='user3', password='user3', email='user3@example.com')
        client = APIClient()

        client.force_authenticate(user2)
        subscribe_url = reverse('pybb:add_subscription', args=[topic.id])
        response = client.get(topic.get_absolute_url())
        subscribe_links = html.fromstring(response.content).xpath('//a[@href="%s"]' % subscribe_url)
        self.assertEqual(len(subscribe_links), 1)

        response = client.get(subscribe_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(user2, topic.subscribers.all())

        topic.subscribers.add(user3)

        # create a new reply (with another user)
        client.force_authenticate(superuser)
        add_post_url = reverse('pybb:add_post', args=[topic.id])
        response = client.get(add_post_url)
        values = self.get_form_values(response)
        values['body'] = 'test subscribtion юникод'
        response = client.post(add_post_url, values, follow=True)
        self.assertEqual(response.status_code, 200)
        new_post = Post.objects.order_by('-id')[0]

        # there should only be one email in the outbox (to user2) because @example.com are ignored
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], user2.email)
        self.assertTrue([msg for msg in mail.outbox if new_post.get_absolute_url() in msg.body])

        # unsubscribe
        client.force_authenticate(user2)
        self.assertTrue([msg for msg in mail.outbox if new_post.get_absolute_url() in msg.body])
        response = client.get(reverse('pybb:delete_subscription', args=[topic.id]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(user2, topic.subscribers.all())

    @override_settings(PYBB_DISABLE_SUBSCRIPTIONS=True)
    def test_subscription_disabled(self):
        superuser = User.objects.create_superuser('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(category=category, name='foo')
        topic = Topic.objects.create(name='topic', forum=forum, user=superuser)
        user2 = User.objects.create_user(username='user2', password='user2', email='user2@someserver.com')
        user3 = User.objects.create_user(username='user3', password='user3', email='user3@example.com')
        client = APIClient()

        client.force_authenticate(user2)
        subscribe_url = reverse('pybb:add_subscription', args=[topic.id])
        response = client.get(topic.get_absolute_url())
        subscribe_links = html.fromstring(response.content).xpath('//a[@href="%s"]' % subscribe_url)
        self.assertEqual(len(subscribe_links), 0)

        response = client.get(subscribe_url, follow=True)
        self.assertEqual(response.status_code, 403)

        self.topic.subscribers.add(user3)

        # create a new reply (with another user)
        self.client.force_authenticate(superuser)
        add_post_url = reverse('pybb:add_post', args=[topic.id])
        response = self.client.get(add_post_url)
        values = self.get_form_values(response)
        values['body'] = 'test subscribtion юникод'
        response = self.client.post(add_post_url, values, follow=True)
        self.assertEqual(response.status_code, 200)
        new_post = Post.objects.order_by('-id')[0]

        # there should be one email in the outbox (user3)
        # because already subscribed users will still receive notifications.
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], user3.email)

    @override_settings(PYBB_DISABLE_NOTIFICATIONS=True)
    def test_notifications_disabled(self):
        superuser = User.objects.create_superuser('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(category=category, name='foo')
        topic = Topic.objects.create(name='topic', forum=forum, user=superuser)
        user2 = User.objects.create_user(username='user2', password='user2', email='user2@someserver.com')
        user3 = User.objects.create_user(username='user3', password='user3', email='user3@example.com')
        client = APIClient()

        client.force_authenticate(user2)
        subscribe_url = reverse('pybb:add_subscription', args=[topic.id])
        response = client.get(subscribe_url, follow=True)
        self.assertEqual(response.status_code, 405, 'GET requests should not change subscriptions')

        response = client.post(subscribe_url, follow=True)
        self.assertEqual(response.status_code, 200)

        topic.subscribers.add(user3)

        # create a new reply (with another user)
        self.client.force_authenticate(superuser)
        add_post_url = reverse('pybb:add_post')
        values = {
            'body': 'test subscribtion юникод',
            'topic': topic.id
        }
        response = self.client.post(add_post_url, values, follow=True)
        self.assertEqual(response.status_code, 201)

        # there should be no email in the outbox
        self.assertEqual(len(mail.outbox), 0)

    @skipUnlessDBFeature('supports_microsecond_precision')
    def test_topic_updated(self):
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(category=category, name='foo')
        topic = Topic(name='new topic', forum=forum, user=user)
        topic.save()
        post = Post(topic=topic, user=user, body='bbcode [b]test[/b]')
        post.save()
        client = Client()
        response = client.get(forum.get_absolute_url())
        self.assertEqual(response.context['topic_list'][0], topic)
        post = Post(topic=topic, user=user, body='bbcode [b]test[/b]')
        post.save()
        client = Client()
        response = client.get(forum.get_absolute_url())
        self.assertEqual(response.context['topic_list'][0], topic)

    def test_topic_deleted(self):
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum_1 = Forum.objects.create(name='new forum', category=category)
        topic_1 = Topic.objects.create(name='new topic', forum=forum_1, user=user)
        post_1 = Post.objects.create(topic=topic_1, user=user, body='test')
        post_1 = Post.objects.get(id=post_1.id)

        self.assertAlmostEqual(topic_1.updated, post_1.created, delta=datetime.timedelta(milliseconds=50))
        self.assertAlmostEqual(forum_1.updated, post_1.created, delta=datetime.timedelta(milliseconds=50))

        topic_2 = Topic.objects.create(name='another topic', forum=forum_1, user=user)
        post_2 = Post.objects.create(topic=topic_2, user=user, body='another test')
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
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        response = self.client.get(reverse('pybb:user', kwargs={'username': user.username}))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('pybb:user_posts', kwargs={'username': user.username}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object_list'].count(), 1)

        response = self.client.get(reverse('pybb:user_topics', kwargs={'username': user.username}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object_list'].count(), 1)
        forum_1 = Forum.objects.create(name='new forum', category=category)
        topic_1 = Topic.objects.create(name='new topic', forum=forum_1, user=user)
        topic_1.forum.hidden = True
        topic_1.forum.save()

        self.client.logout()

        response = self.client.get(reverse('pybb:user_posts', kwargs={'username': user.username}))
        self.assertEqual(response.context['object_list'].count(), 0)

        response = self.client.get(reverse('pybb:user_topics', kwargs={'username': user.username}))
        self.assertEqual(response.context['object_list'].count(), 0)

    def test_post_count(self):
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(category=category, name='foo')
        topic = Topic(name='etopic', forum=forum, user=user)
        topic.save()
        post = Post(topic=topic, user=user, body='test') # another post
        post.save()
        self.assertEqual(util.get_pybb_profile(user).user.posts.count(), 1)
        post.body = 'test2'
        post.save()
        self.assertEqual(Profile.objects.get(pk=util.get_pybb_profile(user).pk).user.posts.count(), 1)
        post.delete()
        self.assertEqual(Profile.objects.get(pk=util.get_pybb_profile(user).pk).user.posts.count(), 0)

    def test_latest_topics_tag(self):
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(category=category, name='foo')
        for i in range(10):
            Topic.objects.create(name='topic%s' % i, user=user, forum=forum)
        latest_topics = pybb_get_latest_topics(context=None, user=user)
        self.assertEqual(len(latest_topics), 5)
        self.assertEqual(latest_topics[0].name, 'topic9')
        self.assertEqual(latest_topics[4].name, 'topic5')

    def test_latest_posts_tag(self):
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(category=category, name='foo')
        topic = Topic.objects.create(name='topic', user=user, forum=forum)
        for i in range(10):
            Post.objects.create(body='post%s' % i, user=user, topic=topic)
        latest_topics = pybb_get_latest_posts(context=None, user=user)
        self.assertEqual(len(latest_topics), 5)
        self.assertEqual(latest_topics[0].body, 'post9')
        self.assertEqual(latest_topics[4].body, 'post5')
