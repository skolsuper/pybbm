from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.urlresolvers import reverse
from django.http import Http404
from django.test import TestCase, override_settings, RequestFactory
from lxml import html
from rest_framework.exceptions import NotFound

from pybb.models import Category, Forum, Topic, Post
from pybb.settings import settings as pybb_settings
from pybb.tests.utils import User, Profile
from pybb.views import CategoryView, ForumView, TopicView

Exc404 = (Http404, NotFound)


class HiddenCategoryTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super(HiddenCategoryTest, cls).setUpClass()
        # create users
        cls.staff = User.objects.create_user('staff', 'staff@localhost', 'staff', is_staff=True)
        cls.no_staff = User.objects.create_user('nostaff', 'nostaff@localhost', 'nostaff', is_staff=False)

        # create topic, post in hidden category
        cls.category = Category(name='private', hidden=True)
        cls.category.save()
        cls.forum = Forum.objects.create(name='priv1', category=cls.category)
        cls.topic = Topic.objects.create(name='a topic', forum=cls.forum, user=cls.staff)
        cls.post = Post.objects.create(body='body post', topic=cls.topic, user=cls.staff, on_moderation=True)

        cls.factory = RequestFactory()

    @classmethod
    def tearDownClass(cls):
        cls.staff.delete()
        cls.no_staff.delete()
        cls.category.delete()
        super(HiddenCategoryTest, cls).tearDownClass()

    def test_hidden_category(self):
        # access without user should get 404
        category_view_func = CategoryView.as_view()
        request = self.factory.get(self.category.get_absolute_url())
        request.user = AnonymousUser()
        self.assertRaises(Exc404, category_view_func, request, pk=self.category.pk)
        # access with (unauthorized) user should get 404
        request.user = self.no_staff
        r = category_view_func(request, pk=self.category.pk)
        self.assertRaises(Exc404, category_view_func, request, pk=self.category.pk)
        # allowed user is allowed
        request.user = self.staff
        r = category_view_func(request, pk=self.category.pk)
        self.assertEquals(r.status_code, 200)

    def test_hidden_forum(self):
        # access without user should get 404
        forum_view_func = ForumView.as_view()
        request = self.factory.get(self.forum.get_absolute_url())
        request.user = AnonymousUser()
        self.assertRaises(Exc404, forum_view_func, request, pk=self.forum.pk)
        # access with (unauthorized) user should get 404
        request.user = self.no_staff
        self.assertRaises(Exc404, forum_view_func, request, pk=self.forum.pk)
        # allowed user is allowed
        request.user = self.staff
        r = forum_view_func(request, pk=self.forum.pk)
        self.assertEquals(r.status_code, 200)

    def test_hidden_topic(self):
        topic_view_func = TopicView.as_view()
        request = self.factory.get(self.topic.get_absolute_url())
        # access without user should be redirected
        request.user = AnonymousUser()
        self.assertRaises(Exc404, topic_view_func, request, pk=self.topic.pk)
        # access with (unauthorized) user should get 403 (forbidden)
        request.user = self.no_staff
        self.assertRaises(Exc404, topic_view_func, request, pk=self.topic.pk)
        # allowed user is allowed
        request.user = self.staff
        r = topic_view_func(request, pk=self.topic.id)
        self.assertEquals(r.status_code, 200)

    def test_hidden_post(self):
        # access without user should be redirected
        r = self.get_with_user(self.post.get_absolute_url())
        self.assertRedirects(r, settings.LOGIN_URL + '?next=%s' % self.post.get_absolute_url())
        # access with (unauthorized) user should get 403 (forbidden)
        r = self.get_with_user(self.post.get_absolute_url(), 'nostaff', 'nostaff')
        self.assertEquals(r.status_code, 403)
        # allowed user is allowed
        r = self.get_with_user(self.post.get_absolute_url(), 'staff', 'staff')
        self.assertEquals(r.status_code, 302)

    @override_settings(PYBB_ENABLE_ANONYMOUS_POST=False)
    def test_anon_topic_add(self):
        with self.settings(PYBB_PERMISSION_HANDLER='pybb.tests.RestrictEditingHandler'):
            # access without user should be redirected
            add_topic_url = reverse('pybb:add_topic', kwargs={'forum_id': self.forum.id})
            r = self.get_with_user(add_topic_url)
            self.assertRedirects(r, settings.LOGIN_URL + '?next=%s' % add_topic_url)

            # access with (unauthorized) user should get 403 (forbidden)
            r = self.get_with_user(add_topic_url, 'staff', 'staff')
            self.assertEquals(r.status_code, 403)

        # allowed user is allowed
        r = self.get_with_user(add_topic_url, 'staff', 'staff')
        self.assertEquals(r.status_code, 200)

    def test_redirect_post_edit(self):
        with self.settings(PYBB_PERMISSION_HANDLER='pybb.tests.RestrictEditingHandler'):
            # access without user should be redirected
            edit_post_url = reverse('pybb:edit_post', kwargs={'pk': self.post.id})
            r = self.get_with_user(edit_post_url)
            self.assertRedirects(r, settings.LOGIN_URL + '?next=%s' % edit_post_url)

            # access with (unauthorized) user should get 403 (forbidden)
            r = self.get_with_user(edit_post_url, 'staff', 'staff')
            self.assertEquals(r.status_code, 403)

        # allowed user is allowed
        r = self.get_with_user(edit_post_url, 'staff', 'staff')
        self.assertEquals(r.status_code, 200)

    def test_user_delete_cascade(self):
        user = User.objects.create_user('cronos', 'cronos@localhost', 'cronos')
        profile = getattr(user, pybb_settings.PYBB_PROFILE_RELATED_NAME, None)
        self.assertIsNotNone(profile)
        post = Post(topic=self.topic, user=user, body='I \'ll be back')
        post.save()
        user_pk = user.pk
        profile_pk = profile.pk
        post_pk = post.pk

        user.delete()
        self.assertFalse(User.objects.filter(pk=user_pk).exists())
        self.assertFalse(Profile.objects.filter(pk=profile_pk).exists())
        self.assertFalse(Post.objects.filter(pk=post_pk).exists())

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