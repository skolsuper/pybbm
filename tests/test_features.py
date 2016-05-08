# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import override_settings
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


def test_profile_edit(user, api_client):
    edit_profile_url = reverse('pybb:edit_profile')

    values = {'signature': 'test signature'}
    response = api_client.patch(edit_profile_url, data=values)
    assert response.status_code in (401, 403)

    api_client.force_authenticate(user)
    response = api_client.patch(edit_profile_url, data=values)
    assert response.status_code == 200

    values['signature'] = ''
    response = api_client.patch(edit_profile_url, data=values)
    assert response.status_code == 200


def test_pagination(forum, user, api_client):
    page_size = pybb_settings.PYBB_DEFAULT_TOPICS_PER_PAGE
    for i in range(page_size + 3):
        topic = Topic(name='topic_%s_' % i, forum=forum, user=user)
        topic.save()
    response = api_client.get(reverse('pybb:topic_list'), data={'forum': forum.id})
    assert response.data['count'] == page_size + 3
    assert len(response.data['results']) == page_size
    assert response.data['next']


def test_topic_addition(user, forum, api_client):
    api_client.force_authenticate(user)
    values = {
        'forum': forum.id,
        'body': 'test body',
        'name': 'new topic name',
        'poll_type': Topic.POLL_TYPE_NONE,
    }
    add_topic_url = reverse('pybb:topic_list')
    response = api_client.post(add_topic_url, data=values)
    assert response.status_code == 201
    assert Topic.objects.filter(name='new topic name').exists()


def test_post_deletion(user, topic, forum):
    Post.objects.create(topic=topic, user=user, body='1st post!', user_ip='0.0.0.0')
    not_first = Post.objects.create(topic=topic, user=user, body='I\'m first!', user_ip='0.0.0.0')
    not_first.delete()
    Topic.objects.get(id=topic.id)
    Forum.objects.get(id=forum.id)


def test_topic_deletion(user, forum, topic):
    Post.objects.create(topic=topic, user=user, body='one', user_ip='0.0.0.0')
    post = Post.objects.create(topic=topic, user=user, body='two', user_ip='0.0.0.0')
    post.delete()
    Topic.objects.get(id=topic.id)
    Forum.objects.get(id=forum.id)
    topic.delete()
    Forum.objects.get(id=forum.id)


def test_forum_updated(user, forum, topic, precision_time):
    post = Post.objects.create(topic=topic, user=user, body='one', user_ip='0.0.0.0')
    assert abs(forum.updated - post.created) < datetime.timedelta(milliseconds=50)


def test_latest_topics(user, forum, api_client, precision_time):
    category_2 = Category.objects.create(name='cat2')
    forum_2 = Forum.objects.create(name='forum_2', category=category_2)
    topic_1 = Topic.objects.create(name='topic_1', forum=forum, user=user)
    topic_3 = Topic.objects.create(name='topic_3', forum=forum_2, user=user)

    topic_2 = Topic.objects.create(name='topic_2', forum=forum, user=user)

    Post.objects.create(topic=topic_1, user=user, body='Something completely different', user_ip='0.0.0.0')
    topic_list_url = reverse('pybb:topic_list')

    api_client.force_authenticate(user)
    response = api_client.get(topic_list_url)
    assert response.status_code == 200
    id_list = py_(response.data['results']).pluck('id').value()
    assert id_list == [topic_1.id, topic_2.id, topic_3.id]

    topic_2.forum.hidden = True
    topic_2.forum.save()
    response = api_client.get(topic_list_url)
    id_list = py_(response.data['results']).pluck('id').value()
    assert id_list == [topic_3.id]

    topic_2.forum.hidden = False
    topic_2.forum.save()
    category_2.hidden = True
    category_2.save()
    response = api_client.get(topic_list_url)
    id_list = py_(response.data['results']).pluck('id').value()
    assert id_list == [topic_1.id, topic_2.id]

    topic_2.forum.hidden = False
    topic_2.forum.save()
    category_2.hidden = False
    category_2.save()
    topic_1.on_moderation = True
    topic_1.save()
    response = api_client.get(topic_list_url)
    id_list = py_(response.data['results']).pluck('id').value()
    assert id_list, [topic_1.id, topic_2.id, topic_3.id]

    topic_1.user = User.objects.create_user('another', 'another@localhost', 'another')
    topic_1.save()
    response = api_client.get(topic_list_url)
    id_list = py_(response.data['results']).pluck('id').value()
    assert id_list == [topic_2.id, topic_3.id]

    topic_1.forum.moderators.add(user)
    response = api_client.get(topic_list_url)
    id_list = py_(response.data['results']).pluck('id').value()
    assert id_list == [topic_1.id, topic_2.id, topic_3.id]

    topic_1.forum.moderators.remove(user)
    user.is_superuser = True
    user.save()
    response = api_client.get(topic_list_url)
    id_list = py_(response.data['results']).pluck('id').value()
    assert id_list == [topic_1.id, topic_2.id, topic_3.id]

    api_client.logout()
    response = api_client.get(topic_list_url)
    id_list = py_(response.data['results']).pluck('id').value()
    assert id_list == [topic_2.id, topic_3.id]


def test_inactive(user, topic, api_client):
    api_client.force_authenticate(user)
    url = reverse('pybb:post_list')
    data = {
        'body': 'test ban',
        'topic': topic.id
    }
    response = api_client.post(url, data)
    assert response.status_code == 201
    assert Post.objects.filter(body='test ban').exists()
    inactive_user = User.objects.create_user('inactive_user')
    inactive_user.is_active = False
    inactive_user.save()
    data['body'] = 'test ban 2'
    api_client.force_authenticate(inactive_user)
    response = api_client.post(url, data)
    assert response.status_code == 403
    assert not Post.objects.filter(body='test ban 2').exists()


def test_user_blocking(user, topic, api_client):
    superuser = User.objects.create_superuser('test', 'test@localhost', 'test')
    Post.objects.create(topic=topic, user=user, body='test 1', user_ip='0.0.0.0')
    Post.objects.create(topic=topic, user=user, body='test 2', user_ip='0.0.0.0')
    api_client.force_authenticate(superuser)
    response = api_client.get(reverse('pybb:block_user', args=[user.username]))
    assert response.status_code == 405
    response = api_client.post(reverse('pybb:block_user', args=[user.username]))
    assert response.status_code == 200
    user = User.objects.get(username=user.username)
    assert not user.is_active
    assert Topic.objects.count() == 1
    assert Post.objects.filter(user=user).count() == 2

    user.is_active = True
    user.save()
    response = api_client.post(reverse('pybb:block_user', args=[user.username]),
                               data={'block_and_delete_messages': True})
    assert response.status_code == 200
    user = User.objects.get(username=user.username)
    assert not user.is_active
    assert Topic.objects.count() == 0
    assert Post.objects.filter(user=user).count() == 0


def test_user_unblocking(user, api_client):
    superuser = User.objects.create_superuser('test', 'test@localhost', 'test')
    user.is_active = False
    user.save()

    api_client.force_authenticate(superuser)
    response = api_client.get(reverse('pybb:unblock_user', args=[user.username]))
    assert response.status_code == 405
    response = api_client.post(reverse('pybb:unblock_user', args=[user.username]))
    assert response.status_code == 200
    user = User.objects.get(username=user.username)
    assert user.is_active


def test_edit_post(user, topic, api_client, precision_time):
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


def test_topic_updated(user, forum, api_client, precision_time):
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
