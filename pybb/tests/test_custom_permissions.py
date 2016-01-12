# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.db.models import Q
from django.test import override_settings
from rest_framework.test import APITestCase

from pybb import permissions
from pybb.models import Category, Forum, Topic, Post
from pybb.tests.utils import User


@override_settings(PYBB_PERMISSION_HANDLER='pybb.tests.CustomPermissionHandler')
class CustomPermissionHandlerTest(APITestCase):
    """ test custom permission handler """

    @classmethod
    def setUpClass(cls):
        super(CustomPermissionHandlerTest, cls).setUpClass()
        cls.user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        cls.c_pub = Category.objects.create(name='public')
        cls.c_hid = Category.objects.create(name='private', hidden=True)

    @classmethod
    def tearDownClass(cls):
        cls.user.delete()
        Category.objects.all().delete()
        super(CustomPermissionHandlerTest, cls).tearDownClass()

    def test_category_permission(self):
        categories = Category.objects.all()
        self.client.force_authenticate()
        for c in categories:
            # anon user may not see category
            r = self.client.get(c.get_absolute_url())
            if c.hidden:
                self.assertEqual(r.status_code, 404)
            else:
                self.assertEqual(r.status_code, 200)
                # logged on user may see all categories

        self.client.force_authenticate(self.user)
        for c in categories:
            # custom permissions: regular users can see hidden categories
            r = self.client.get(c.get_absolute_url())
            self.assertEqual(r.status_code, 200)

    def test_forum_permission(self):
        Forum.objects.create(name='public forum', category=self.c_pub)
        Forum.objects.create(name='hidden forum', category=self.c_hid)
        self.client.force_authenticate()
        forums = Forum.objects.all()
        for f in forums:
            r = self.client.get(f.get_absolute_url())
            self.assertEqual(r.status_code, 404 if f.hidden or f.category.hidden else 200)
        self.client.force_authenticate(self.user)
        for f in forums:
            r = self.client.get(f.get_absolute_url())
            self.assertEqual(r.status_code, 200)

    def test_topic_permission(self):
        f_pub = Forum.objects.create(name='public forum', category=self.c_pub)
        f_hid = Forum.objects.create(name='hidden forum', category=self.c_hid)
        Topic.objects.create(user=self.user, forum=f_pub, name='public topic')
        Topic.objects.create(user=self.user, forum=f_pub, name='public closed topic')
        Topic.objects.create(user=self.user, forum=f_hid, name='hidden topic')
        Topic.objects.create(user=self.user, forum=f_hid, name='hidden closed topic')
        for t in Topic.objects.all():
            Post.objects.create(user=self.user, topic=t, body='test', user_ip='0.0.0.0')
        Topic.objects.filter(name__contains='closed').update(closed=True)

        topics = Topic.objects.all()
        self.client.force_authenticate()
        for t in topics:
            r = self.client.get(t.get_absolute_url())
            self.assertEqual(r.status_code, 404 if t.forum.hidden or t.forum.category.hidden or t.closed else 200)

        self.client.login(username='zeus', password='zeus')  # force_authenticate doesn't work here for some reason
        for t in topics:
            r = self.client.get(t.get_absolute_url())
            self.assertEqual(r.status_code, 404 if t.closed else 200)

        # custom permission filters closed topics from topic list.
        r = self.client.get(reverse('pybb:topic_list'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 2)

    def test_post_permission(self):
        f_pub = Forum.objects.create(name='public forum', category=self.c_pub)
        f_hid = Forum.objects.create(name='hidden forum', category=self.c_hid)
        Topic.objects.create(user=self.user, forum=f_pub, name='public topic')
        Topic.objects.create(user=self.user, forum=f_pub, name='public closed topic')
        Topic.objects.create(user=self.user, forum=f_hid, name='hidden topic')
        Topic.objects.create(user=self.user, forum=f_hid, name='hidden closed topic')
        for t in Topic.objects.all():
            Post.objects.create(user=self.user, topic=t, body='test', user_ip='0.0.0.0')
        Topic.objects.filter(name__contains='closed').update(closed=True)

        self.client.force_authenticate()
        all_posts = Post.objects.all()
        for p in all_posts:
            r = self.client.get(p.get_absolute_url())
            self.assertEqual(r.status_code, 404 if p.topic.forum.hidden or p.topic.forum.category.hidden else 200)
        self.client.force_authenticate(self.user)
        for p in all_posts:
            r = self.client.get(p.get_absolute_url())
            self.assertEqual(r.status_code, 200)

    def test_poll_add(self):
        forum = Forum.objects.create(name='public forum', category=self.c_pub)
        add_topic_url = reverse('pybb:topic_list')
        values = {
            'forum': forum.id,
            'body': 'test poll body',
            'name': 'test poll name',
            'poll_type': Topic.POLL_TYPE_SINGLE,
            'poll_question': 'q1',
            'poll_answers': [
                {'text': 'answer1'},
                {'text': 'answer2'},
            ]
        }
        self.client.force_authenticate(self.user)
        response = self.client.post(add_topic_url, values, follow=True)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Topic.objects.filter(name='test poll name').exists())


class CustomPermissionHandler(permissions.DefaultPermissionHandler):
    """
    a custom permission handler which changes the meaning of "hidden" forum:
    "hidden" forum or category is visible for all logged on users, not only staff
    """

    def filter_categories(self, user, qs):
        return qs.filter(hidden=False) if user.is_anonymous() else qs

    def may_view_category(self, user, category):
        return user.is_authenticated() if category.hidden else True

    def filter_forums(self, user, qs):
        if user.is_anonymous():
            qs = qs.filter(Q(hidden=False) & Q(category__hidden=False))
        return qs

    def may_view_forum(self, user, forum):
        return user.is_authenticated() if forum.hidden or forum.category.hidden else True

    def filter_topics(self, user, qs):
        if user.is_anonymous():
            qs = qs.filter(Q(forum__hidden=False) & Q(forum__category__hidden=False))
        qs = qs.filter(closed=False)  # filter out closed topics for test
        return qs

    def may_view_topic(self, user, topic):
        return self.may_view_forum(user, topic.forum)

    def filter_posts(self, user, qs):
        if user.is_anonymous():
            qs = qs.filter(Q(topic__forum__hidden=False) & Q(topic__forum__category__hidden=False))
        return qs

    def may_view_post(self, user, post):
        return self.may_view_forum(user, post.topic.forum)

    def may_create_poll(self, user):
        return False

    def may_edit_topic_slug(self, user):
        return True


class RestrictEditingHandler(permissions.DefaultPermissionHandler):
    def may_create_topic(self, user, forum):
        return False

    def may_create_post(self, user, topic):
        return False

    def may_edit_post(self, user, post):
        return False
