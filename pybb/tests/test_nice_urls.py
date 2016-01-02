# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.test import override_settings
from rest_framework.test import APITestCase

from pybb import compat
from pybb.models import Category, Forum, Topic, Post
from pybb.settings import settings as pybb_settings

User = get_user_model()


@override_settings(PYBB_NICE_URL=True)
class NiceUrlsTest(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(NiceUrlsTest, cls).setUpClass()
        cls.user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        cls.category = Category.objects.create(name='foo')
        cls.forum = Forum.objects.create(name='xfoo', description='bar', category=cls.category)
        cls.topic = Topic.objects.create(name='etopic', forum=cls.forum, user=cls.user)
        cls.post = Post.objects.create(topic=cls.topic, user=cls.user, body='bbcode [b]test[/b]')

    @classmethod
    def tearDownClass(cls):
        cls.category.delete()
        cls.user.delete()
        super(NiceUrlsTest, cls).tearDownClass()

    def setUp(self):
        self.client.force_authenticate(self.user)

    def test_unicode_slugify(self):
        self.assertEqual(compat.slugify('北京 (China), Москва (Russia), é_è (a sad smiley !)'),
                         'bei-jing-china-moskva-russia-e_e-a-sad-smiley')

    def test_automatique_slug(self):
        self.assertEqual(compat.slugify(self.category.name), self.category.slug)
        self.assertEqual(compat.slugify(self.forum.name), self.forum.slug)
        self.assertEqual(compat.slugify(self.topic.name), self.topic.slug)

    def test_no_duplicate_slug(self):
        category_name = self.category.name
        forum_name = self.forum.name
        topic_name = self.topic.name

        # objects created without slug but the same name
        category = Category.objects.create(name=category_name)
        forum = Forum.objects.create(name=forum_name, description='bar', category=self.category)
        topic = Topic.objects.create(name=topic_name, forum=self.forum, user=self.user)

        slug_nb = len(Category.objects.filter(slug__startswith=category_name)) - 1
        self.assertEqual('%s-%d' % (compat.slugify(category_name), slug_nb), category.slug)
        slug_nb = len(Forum.objects.filter(slug__startswith=forum_name)) - 1
        self.assertEqual('%s-%d' % (compat.slugify(forum_name), slug_nb), forum.slug)
        slug_nb = len(Topic.objects.filter(slug__startswith=topic_name)) - 1
        self.assertEqual('%s-%d' % (compat.slugify(topic_name), slug_nb), topic.slug)

        # objects created with a duplicate slug but a different name
        category = Category.objects.create(name='test_slug_category', slug=compat.slugify(category_name))
        forum = Forum.objects.create(name='test_slug_forum', description='bar',
                                     category=self.category, slug=compat.slugify(forum_name))
        topic = Topic.objects.create(name='test_topic_slug', forum=self.forum,
                                     user=self.user, slug=compat.slugify(topic_name))
        slug_nb = len(Category.objects.filter(slug__startswith=category_name)) - 1
        self.assertEqual('%s-%d' % (compat.slugify(category_name), slug_nb), category.slug)
        slug_nb = len(Forum.objects.filter(slug__startswith=forum_name)) - 1
        self.assertEqual('%s-%d' % (compat.slugify(forum_name), slug_nb), forum.slug)
        slug_nb = len(Topic.objects.filter(slug__startswith=self.topic.name)) - 1
        self.assertEqual('%s-%d' % (compat.slugify(topic_name), slug_nb), topic.slug)

    @override_settings(PYBB_NICE_URL_SLUG_DUPLICATE_LIMIT=20)
    def test_fail_on_too_many_duplicate_slug(self):
        try:
            for _ in iter(range(20)):
                Topic.objects.create(name='dolly', forum=self.forum, user=self.user)
        except ValidationError as e:
            self.fail('Should be able to create "dolly", "dolly-1", ..., "dolly-19".\n')
        with self.assertRaises(ValidationError):
            Topic.objects.create(name='dolly', forum=self.forum, user=self.user)

    def test_long_duplicate_slug(self):
        long_name = 'abcde' * 51  # 255 symbols
        topic1 = Topic.objects.create(name=long_name, forum=self.forum, user=self.user)
        self.assertEqual(topic1.slug, long_name)
        topic2 = Topic.objects.create(name=long_name, forum=self.forum, user=self.user)
        self.assertEqual(topic2.slug, '%s-1' % long_name[:253])
        topic3 = Topic.objects.create(name=long_name, forum=self.forum, user=self.user)
        self.assertEqual(topic3.slug, '%s-2' % long_name[:253])

    def test_absolute_url(self):
        response = self.client.get(self.category.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], self.category.name)
        self.assertEqual('/c/%s/' % (self.category.slug), self.category.get_absolute_url())
        response = self.client.get(self.forum.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], self.forum.name)
        self.assertEqual(
            '/c/%s/%s/' % (self.category.slug, self.forum.slug),
            self.forum.get_absolute_url()
            )
        response = self.client.get(self.topic.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], self.topic.name)
        self.assertEqual(
            '/c/%s/%s/%s/' % (self.category.slug, self.forum.slug, self.topic.slug),
            self.topic.get_absolute_url()
            )

    def test_add_topic(self):
        add_topic_url = reverse('pybb:topic_list')
        values = {
            'name': self.topic.name,
            'body': '[b]Test slug body[/b]',
            'forum': self.forum.id,
            'poll_type': Topic.POLL_TYPE_NONE
        }
        self.client.post(add_topic_url, data=values, follow=True)
        slug_nb = Topic.objects.filter(slug__regex='^{}-?\d*'.format(compat.slugify(self.topic.name))).count() - 1
        Topic.objects.get(slug='%s-%d' % (self.topic.name, slug_nb))

        with self.settings(PYBB_PERMISSION_HANDLER='pybb.tests.CustomPermissionHandler'):
            values = {
                'name': self.topic.name,
                'body': '[b]Test slug body[/b]',
                'forum': self.forum.id,
                'poll_type': Topic.POLL_TYPE_NONE,
                'slug': 'test-slug'
            }
            self.client.post(add_topic_url, data=values, follow=True)
            Topic.objects.get(slug='test-slug')

    def test_old_url_redirection(self):

        original_perm_redirect = pybb_settings.PYBB_NICE_URL_PERMANENT_REDIRECT

        for redirect_status in [301, 302]:
            pybb_settings.PYBB_NICE_URL_PERMANENT_REDIRECT = redirect_status == 301

            response = self.client.get(reverse("pybb:category", kwargs={"pk": self.category.pk}))
            self.assertRedirects(response, self.category.get_absolute_url(), status_code=redirect_status)

            response = self.client.get(reverse("pybb:forum", kwargs={"pk": self.forum.pk}))
            self.assertRedirects(response, self.forum.get_absolute_url(), status_code=redirect_status)

            response = self.client.get(reverse("pybb:topic", kwargs={"pk": self.topic.pk}))
            self.assertRedirects(response, self.topic.get_absolute_url(), status_code=redirect_status)

        pybb_settings.PYBB_NICE_URL_PERMANENT_REDIRECT = original_perm_redirect

