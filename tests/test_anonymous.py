# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.test import override_settings
from lxml import html
from rest_framework.test import APITestCase

from pybb import util
from pybb.models import Category, Forum, Topic, Post
from pybb.settings import settings as pybb_settings
User = get_user_model()


@override_settings(PYBB_ENABLE_ANONYMOUS_POST=True, PYBB_ANONYMOUS_USERNAME='Anonymous')
class AnonymousTest(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(AnonymousTest, cls).setUpClass()
        cls.user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        cls.category = Category.objects.create(name='foo')
        cls.forum = Forum.objects.create(name='xfoo', description='bar', category=cls.category)
        cls.topic = Topic.objects.create(name='etopic', forum=cls.forum, user=cls.user)
        cls.post = Post.objects.create(body='body post', topic=cls.topic, user=cls.user, user_ip='0.0.0.0')
        add_post_permission = Permission.objects.get_by_natural_key('add_post', 'pybb', 'post')
        cls.user.user_permissions.add(add_post_permission)

    @classmethod
    def tearDownClass(cls):
        cls.user.delete()
        cls.category.delete()
        super(AnonymousTest, cls).tearDownClass()

    def setUp(self):
        cache.clear()

    def test_anonymous_posting(self):
        self.client.force_authenticate()
        post_url = reverse('pybb:post_list')
        values = {
            'topic': self.topic.id,
            'body': 'test anonymous'
        }
        response = self.client.post(post_url, values, follow=True)
        self.assertEqual(response.status_code, 201,
                         'Received status code {0}. Url was: {1}'.format(response.status_code, post_url))
        self.assertEqual(Post.objects.filter(body='test anonymous').count(), 1)
        self.assertIsNone(Post.objects.get(body='test anonymous').user)

    @override_settings(PYBB_ENABLE_ANONYMOUS_POST=False)
    def test_no_anonymous_posting(self):
        self.client.force_authenticate()
        post_url = reverse('pybb:post_list')
        values = {
            'topic': self.topic.id,
            'body': 'test anonymous'
        }
        response = self.client.post(post_url, values, follow=True)
        self.assertIn(response.status_code, (401, 403),
                      'Received status code {0}. Url was: {1}'.format(response.status_code, post_url))
        self.assertEqual(Post.objects.filter(body='test anonymous').count(), 0)

    def test_anonymous_cache_topic_views(self):
        self.assertNotIn(util.build_cache_key('anonymous_topic_views', topic_id=self.topic.id), cache)
        url = self.topic.get_absolute_url()
        self.client.get(url)
        self.assertEqual(cache.get(util.build_cache_key('anonymous_topic_views', topic_id=self.topic.id)), 1)
        for _ in range(pybb_settings.PYBB_ANONYMOUS_VIEWS_CACHE_BUFFER - 2):
            self.client.get(url)
        self.assertEqual(Topic.objects.get(id=self.topic.id).views, 0)
        self.assertEqual(cache.get(util.build_cache_key('anonymous_topic_views', topic_id=self.topic.id)),
                         pybb_settings.PYBB_ANONYMOUS_VIEWS_CACHE_BUFFER - 1)
        self.client.get(url)
        self.assertEqual(Topic.objects.get(id=self.topic.id).views, pybb_settings.PYBB_ANONYMOUS_VIEWS_CACHE_BUFFER)
        self.assertEqual(cache.get(util.build_cache_key('anonymous_topic_views', topic_id=self.topic.id)), 0)

        views = Topic.objects.get(id=self.topic.id).views

        pybb_settings.PYBB_ANONYMOUS_VIEWS_CACHE_BUFFER = None
        self.client.get(url)
        self.assertEqual(Topic.objects.get(id=self.topic.id).views, views + 1)
        self.assertEqual(cache.get(util.build_cache_key('anonymous_topic_views', topic_id=self.topic.id)), 0)

    def create_user(self):
        self.user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')

    def login_client(self, username='zeus', password='zeus'):
        self.client.login(username=username, password=password)

    def create_initial(self, post=True):
        self.category = Category.objects.create(name='foo')
        self.forum = Forum.objects.create(name='xfoo', description='bar', category=self.category)
        self.topic = Topic.objects.create(name='etopic', forum=self.forum, user=self.user)
        if post:
            self.post = Post.objects.create(topic=self.topic, user=self.user, body='bbcode [b]test[/b]', user_ip='0.0.0.0')

    def get_form_values(self, response, form="post-form"):
        return dict(html.fromstring(response.content).xpath('//form[@class="%s"]' % form)[0].form_values())

    def get_with_user(self, url, username=None, password=None):
        if username:
            self.client.login(username=username, password=password)
        r = self.client.get(url)
        self.client.logout()
        return r
