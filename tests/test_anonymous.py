# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest
from django.core.cache import cache
from django.core.urlresolvers import reverse
from rest_framework.settings import api_settings

from pybb import util
from pybb.models import Topic, Post


@pytest.fixture()
def anonymous_post_on(settings):
    settings.PYBB_ENABLE_ANONYMOUS_POST = True
    settings.PYBB_ANONYMOUS_VIEWS_CACHE_BUFFER = 10

@pytest.fixture()
def auth_header(rf):
    return api_settings.DEFAULT_AUTHENTICATION_CLASSES[0]().authenticate_header(rf.get('/'))


@pytest.mark.usefixtures('anonymous_post_on')
class AnonymousTestSuite(object):

    def test_anonymous_posting(self, topic, api_client):
        api_client.force_authenticate()
        post_url = reverse('pybb:post_list')
        values = {
            'topic': topic.id,
            'body': 'test anonymous'
        }
        response = api_client.post(post_url, values)
        assert response.status_code == 201, 'Received status code {0}. Url was: {1}'.format(response.status_code, post_url)
        assert Post.objects.filter(body='test anonymous').count() == 1
        assert Post.objects.get(body='test anonymous').user is None

    def test_anonymous_cache_topic_views(self, settings, topic, api_client, auth_header):
        cache.clear()
        assert util.build_cache_key('anonymous_topic_views', topic_id=topic.id) not in cache
        url = topic.get_absolute_url()
        api_client.get(url)
        assert cache.get(util.build_cache_key('anonymous_topic_views', topic_id=topic.id)) == 1

        for _ in range(8):
            api_client.get(url)
        assert Topic.objects.get(id=topic.id).views == 0
        assert cache.get(util.build_cache_key('anonymous_topic_views', topic_id=topic.id)) == 9

        api_client.get(url)
        assert Topic.objects.get(id=topic.id).views == 10
        assert cache.get(util.build_cache_key('anonymous_topic_views', topic_id=topic.id)) == 0

        view_count = Topic.objects.get(id=topic.id).views

        settings.PYBB_ANONYMOUS_VIEWS_CACHE_BUFFER = None
        api_client.get(url)
        assert Topic.objects.get(id=topic.id).views == view_count + 1
        assert cache.get(util.build_cache_key('anonymous_topic_views', topic_id=topic.id)) == 0

    def test_no_anonymous_posting(self, settings, topic, api_client):
        settings.PYBB_ENABLE_ANONYMOUS_POST = False
        api_client.force_authenticate()
        post_url = reverse('pybb:post_list')
        values = {
            'topic': topic.id,
            'body': 'test anonymous'
        }
        response = api_client.post(post_url, values)
        assert response.status_code == 403 if auth_header is None else 401
        assert Post.objects.filter(body='test anonymous').count() == 0

    def test_anon_topic_add_custom_settings(self, settings, forum, user, api_client, auth_header):
        settings.PYBB_ENABLE_ANONYMOUS_POST = False
        settings.PYBB_PERMISSION_HANDLER = 'test.test_project.permissions.RestrictEditingHandler'
        add_topic_url = reverse('pybb:topic_list')
        values = {
            'forum': forum.id,
            'name': 'test topic',
            'body': 'test topic body',
            'poll_type': Topic.POLL_TYPE_NONE
        }
        response = api_client.post(add_topic_url, values)
        assert response.status_code == 403 if auth_header is None else 401

        # access with (unauthorized) user should get 403 (forbidden)
        api_client.force_authenticate(user)
        response = api_client.post(add_topic_url, values)
        assert response.status_code == 403

    def test_anon_topic_add_default_settings(self, settings, forum, user, api_client):
        settings.PYBB_ENABLE_ANONYMOUS_POST = False
        add_topic_url = reverse('pybb:topic_list')
        values = {
            'forum': forum.id,
            'name': 'test topic',
            'body': 'test topic body',
            'poll_type': Topic.POLL_TYPE_NONE
        }
        api_client.force_authenticate(user)
        response = api_client.post(add_topic_url, values)
        assert response.status_code == 201
