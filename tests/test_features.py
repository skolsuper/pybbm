# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.urlresolvers import reverse
from django.db import connection
from django.test import skipUnlessDBFeature, Client, override_settings
from pydash import py_
from rest_framework.test import APITestCase

from pybb import util
from pybb.models import Forum, Topic, Post, Category
from pybb.settings import settings as pybb_settings
from pybb.templatetags.pybb_tags import pybb_get_latest_topics, pybb_get_latest_posts
User = get_user_model()
Profile = util.get_pybb_profile_model()


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
        post = Post.objects.create(topic=topic, user=user, body='bbcode [b]test[/b]', user_ip='0.0.0.0')
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
        Post.objects.create(topic=topic, user=user, body='one', user_ip='0.0.0.0')
        post = Post.objects.create(topic=topic, user=user, body='two', user_ip='0.0.0.0')
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
        post = Post.objects.create(topic=topic, user=user, body='one', user_ip='0.0.0.0')
        self.assertAlmostEqual(forum.updated, post.created, delta=datetime.timedelta(milliseconds=50))

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

        Post.objects.create(topic=topic_1, user=user, body='Something completely different', user_ip='0.0.0.0')
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
        url = reverse('pybb:post_list')
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
        p1 = Post.objects.create(topic=topic, user=user, body='bbcode [b]test[/b]', user_ip='0.0.0.0')
        p2 = Post.objects.create(topic=topic, user=user, body='bbcode [b]test[/b]', user_ip='0.0.0.0')
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

    def test_headline(self):
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(category=category, name='foo')
        forum.headline = 'test <b>headline</b>'
        forum.save()
        client = Client()
        self.assertContains(client.get(forum.get_absolute_url()), 'test <b>headline</b>')


def test_edit_post(user, topic, api_client):
    if not getattr(connection.features, 'supports_microsecond_precision', False):
        pytest.skip('Database time precision not high enough')
    post = Post.objects.create(topic=topic, user=user, body='bbcode [b]test[/b]', user_ip='0.0.0.0')
    original_updated = post.updated

    api_client.force_authenticate(user)
    edit_post_url = reverse('pybb:edit_post', kwargs={'pk': post.id})
    values = {
        'body': 'test edit',
    }
    response = api_client.patch(edit_post_url, data=values)
    assert response.status_code == 200
    post = Post.objects.get(pk=post.id)
    assert post.body == 'test edit'
    assert post.updated != original_updated


def test_stick(forum, api_client):
    superuser = User.objects.create_superuser('zeus', 'zeus@localhost', 'zeus')
    topic = Topic.objects.create(name='topic', forum=forum, user=superuser)
    api_client.force_authenticate(superuser)
    response = api_client.get(reverse('pybb:stick_topic', kwargs={'pk': topic.id}), follow=True)
    assert response.status_code == 405
    response = api_client.post(reverse('pybb:stick_topic', kwargs={'pk': topic.id}), follow=True)
    assert response.status_code == 200

    response = api_client.get(reverse('pybb:unstick_topic', kwargs={'pk': topic.id}), follow=True)
    assert response.status_code == 405
    response = api_client.post(reverse('pybb:unstick_topic', kwargs={'pk': topic.id}), follow=True)
    assert response.status_code == 200


def test_delete_view(forum, api_client):
    superuser = User.objects.create_superuser('zeus', 'zeus@localhost', 'zeus')
    topic = Topic.objects.create(name='topic', forum=forum, user=superuser)
    topic_head = Post.objects.create(topic=topic, user=superuser, body='test topic head', user_ip='0.0.0.0')
    post = Post.objects.create(topic=topic, user=superuser, body='test to delete', user_ip='0.0.0.0')
    api_client.force_authenticate(superuser)
    response = api_client.delete(reverse('pybb:delete_post', args=[post.id]), follow=True)
    assert response.status_code == 204
    # Check that topic and forum exists ;)
    assert Topic.objects.filter(id=topic.id).count() == 1
    assert Forum.objects.filter(id=forum.id).count() == 1

    # Delete topic
    response = api_client.delete(reverse('pybb:delete_post', args=[topic_head.id]), follow=True)
    assert response.status_code == 204
    assert Post.objects.filter(id=post.id).count() == 0
    assert Topic.objects.filter(id=topic.id).count() == 0
    assert Forum.objects.filter(id=forum.id).count() == 1


def test_open_close(forum, api_client):
    superuser = User.objects.create_superuser('zeus', 'zeus@localhost', 'zeus')
    topic = Topic.objects.create(name='topic', forum=forum, user=superuser)
    api_client.force_authenticate(superuser)
    response = api_client.get(reverse('pybb:close_topic', args=[topic.id]))
    use_post_request_msg = 'Should use a post request to make changes on the server'
    assert response.status_code == 405, use_post_request_msg

    response = api_client.post(reverse('pybb:close_topic', args=[topic.id]))
    assert response.status_code == 200

    add_post_url = reverse('pybb:post_list')
    values = {'body': 'test closed', 'topic': topic.id}
    response = api_client.post(add_post_url, values)
    assert response.status_code == 201, 'Superusers can post in closed topics'

    peon = User.objects.create_user('regular_user')
    api_client.force_authenticate(peon)
    response = api_client.post(add_post_url, values)
    assert response.status_code == 403

    api_client.force_authenticate(superuser)
    response = api_client.get(reverse('pybb:open_topic', args=[topic.id]))
    assert response.status_code, 405 == use_post_request_msg
    response = api_client.post(reverse('pybb:open_topic', args=[topic.id]))
    assert response.status_code == 200

    api_client.force_authenticate(peon)
    response = api_client.post(add_post_url, values)
    assert response.status_code == 201


def test_topic_updated(user, forum, api_client):
    if not getattr(connection.features, 'supports_microsecond_precision', False):
        pytest.skip('Database time precision not high enough')
    topic_1 = Topic.objects.create(name='topic one', forum=forum, user=user)
    topic_2 = Topic.objects.create(name='topic two', forum=forum, user=user)
    Post.objects.create(topic=topic_1, user=user, body='bbcode [b]test[/b]', user_ip='0.0.0.0')
    topic_list_url = reverse('pybb:topic_list')
    response = api_client.get(topic_list_url, data={'forum': forum.id})
    assert response.data['results'][0]['name'] == 'topic one'

    Post.objects.create(topic=topic_2, user=user, body='bbcode [b]test[/b]', user_ip='0.0.0.0')
    response = api_client.get(topic_list_url, data={'forum': forum.id})
    assert response.data['results'][0]['name'] == 'topic two'


def test_topic_deleted(user, forum):
    topic_1 = Topic.objects.create(name='new topic', forum=forum, user=user)
    post_1 = Post.objects.create(topic=topic_1, user=user, body='test', user_ip='0.0.0.0')
    post_1 = Post.objects.get(id=post_1.id)

    assert abs(topic_1.updated - post_1.created) < datetime.timedelta(milliseconds=50)
    assert abs(forum.updated - post_1.created) < datetime.timedelta(milliseconds=50)

    topic_2 = Topic.objects.create(name='another topic', forum=forum, user=user)
    post_2 = Post.objects.create(topic=topic_2, user=user, body='another test', user_ip='0.0.0.0')
    post_2 = Post.objects.get(id=post_2.id)

    assert abs(topic_2.updated - post_2.created) < datetime.timedelta(milliseconds=50)
    assert abs(forum.updated - post_2.created) < datetime.timedelta(milliseconds=50)

    topic_2.delete()
    forum = Forum.objects.get(id=forum.id)
    assert abs(forum.updated - post_1.created) < datetime.timedelta(milliseconds=50)
    assert forum.topics.count() == 1
    assert forum.posts.count() == 1

    post_1.delete()
    forum = Forum.objects.get(id=forum.id)
    assert forum.topics.count() == 0
    assert forum.posts.count() == 0


def test_user_views(forum, user, api_client):
    topic = Topic.objects.create(name='new topic', forum=forum, user=user)
    Post.objects.create(user=user, topic=topic, body='blah', user_ip='0.0.0.0')

    response = api_client.get(reverse('pybb:user_posts', kwargs={'username': user.username}))
    assert response.status_code == 200
    assert response.data['count'] == 1

    response = api_client.get(reverse('pybb:user_topics', kwargs={'username': user.username}))
    assert response.status_code == 200
    assert response.data['count'] == 1

    forum.hidden = True
    forum.save()

    response = api_client.get(reverse('pybb:user_posts', kwargs={'username': user.username}))
    assert response.data['count'] == 0

    response = api_client.get(reverse('pybb:user_topics', kwargs={'username': user.username}))
    assert response.data['count'] == 0


def test_post_count(user, topic):
    post = Post.objects.create(topic=topic, user=user, body='test', user_ip='0.0.0.0')
    assert util.get_pybb_profile(user).user.posts.count() == 1
    post.body = 'test2'
    post.save()
    assert Profile.objects.get(pk=util.get_pybb_profile(user).pk).user.posts.count() == 1
    post.delete()
    assert Profile.objects.get(pk=util.get_pybb_profile(user).pk).user.posts.count() == 0


def test_latest_topics_tag(forum, user):
    for i in range(10):
        Topic.objects.create(name='topic%s' % i, user=user, forum=forum)
    latest_topics = pybb_get_latest_topics(context=None, user=user)
    assert len(latest_topics) == 5
    assert latest_topics[0].name == 'topic9'
    assert latest_topics[4].name == 'topic5'


def test_latest_posts_tag(topic, user):
    for i in range(10):
        Post.objects.create(body='post%s' % i, user=user, topic=topic, user_ip='0.0.0.0')
    latest_topics = pybb_get_latest_posts(context=None, user=user)
    assert len(latest_topics) == 5
    assert latest_topics[0].body == 'post9'
    assert latest_topics[4].body == 'post5'


def test_user_delete_cascade(topic):
    user = User.objects.create_user('cronos', 'cronos@localhost', 'cronos')
    profile = getattr(user, pybb_settings.PYBB_PROFILE_RELATED_NAME, None)
    assert profile is not None
    post = Post.objects.create(topic=topic, user=user, body='I \'ll be back', user_ip='0.0.0.0')
    user_pk = user.pk
    profile_pk = profile.pk
    post_pk = post.pk

    user.delete()
    assert not User.objects.filter(pk=user_pk).exists()
    assert not Profile.objects.filter(pk=profile_pk).exists()
    assert not Post.objects.filter(pk=post_pk).exists()
