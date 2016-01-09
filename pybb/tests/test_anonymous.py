# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.test import TestCase
from lxml import html

from pybb import util
from pybb.models import Category, Forum, Topic, Post
from pybb.settings import settings as pybb_settings
from pybb.tests.utils import User


class AnonymousTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super(AnonymousTest, cls).setUpClass()
        cls.ORIG_PYBB_ENABLE_ANONYMOUS_POST = pybb_settings.PYBB_ENABLE_ANONYMOUS_POST
        cls.ORIG_PYBB_ANONYMOUS_USERNAME = pybb_settings.PYBB_ANONYMOUS_USERNAME
        cls.PYBB_ANONYMOUS_VIEWS_CACHE_BUFFER = pybb_settings.PYBB_ANONYMOUS_VIEWS_CACHE_BUFFER

        pybb_settings.PYBB_ENABLE_ANONYMOUS_POST = True
        pybb_settings.PYBB_ANONYMOUS_USERNAME = 'Anonymous'
        cls.user = User.objects.create_user('Anonymous', 'Anonymous@localhost', 'Anonymous')
        cls.category = Category.objects.create(name='foo')
        cls.forum = Forum.objects.create(name='xfoo', description='bar', category=cls.category)
        cls.topic = Topic.objects.create(name='etopic', forum=cls.forum, user=cls.user)
        cls.post = Post.objects.create(body='body post', topic=cls.topic, user=cls.user)
        add_post_permission = Permission.objects.get_by_natural_key('add_post', 'pybb', 'post')
        cls.user.user_permissions.add(add_post_permission)

    @classmethod
    def tearDownClass(cls):
        pybb_settings.PYBB_ENABLE_ANONYMOUS_POST = cls.ORIG_PYBB_ENABLE_ANONYMOUS_POST
        pybb_settings.PYBB_ANONYMOUS_USERNAME = cls.ORIG_PYBB_ANONYMOUS_USERNAME
        pybb_settings.PYBB_ANONYMOUS_VIEWS_CACHE_BUFFER = cls.PYBB_ANONYMOUS_VIEWS_CACHE_BUFFER
        super(AnonymousTest, cls).tearDownClass()

    def setUp(self):
        cache.clear()

    def test_anonymous_posting(self):
        post_url = reverse('pybb:add_post', kwargs={'topic_id': self.topic.id})
        response = self.client.get(post_url)
        values = self.get_form_values(response)
        values['body'] = 'test anonymous'
        response = self.client.post(post_url, values, follow=True)
        self.assertEqual(response.status_code, 200,
                         'Received status code {0}. Url was: {1}'.format(response.status_code, post_url))
        self.assertEqual(len(Post.objects.filter(body='test anonymous')), 1)
        self.assertEqual(Post.objects.get(body='test anonymous').user, self.user)

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
            self.post = Post.objects.create(topic=self.topic, user=self.user, body='bbcode [b]test[/b]')

    def get_form_values(self, response, form="post-form"):
        return dict(html.fromstring(response.content).xpath('//form[@class="%s"]' % form)[0].form_values())

    def get_with_user(self, url, username=None, password=None):
        if username:
            self.client.login(username=username, password=password)
        r = self.client.get(url)
        self.client.logout()
        return r
