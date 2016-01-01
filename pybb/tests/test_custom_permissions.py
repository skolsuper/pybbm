# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.db.models import Q
from django.test import override_settings, TestCase

from pybb import permissions
from pybb.models import Category, Forum, Topic, Post, PollAnswer
from pybb.tests.utils import SharedTestModule


@override_settings(PYBB_PERMISSION_HANDLER='pybb.tests.CustomPermissionHandler')
class CustomPermissionHandlerTest(TestCase, SharedTestModule):
    """ test custom permission handler """

    def setUp(self):
        self.create_user()
        # create public and hidden categories, forums, posts
        c_pub = Category(name='public')
        c_pub.save()
        c_hid = Category(name='private', hidden=True)
        c_hid.save()
        self.forum = Forum.objects.create(name='pub1', category=c_pub)
        Forum.objects.create(name='priv1', category=c_hid)
        Forum.objects.create(name='private_in_public_cat', hidden=True, category=c_pub)
        for f in Forum.objects.all():
            t = Topic.objects.create(name='a topic', forum=f, user=self.user)
            Post.objects.create(topic=t, user=self.user, body='test')
        # make some topics closed => hidden
        for t in Topic.objects.all()[0:2]:
            t.closed = True
            t.save()

    def test_category_permission(self):
        for c in Category.objects.all():
            # anon user may not see category
            r = self.get_with_user(c.get_absolute_url())
            if c.hidden:
                self.assertEqual(r.status_code, 302)
            else:
                self.assertEqual(r.status_code, 200)
                # logged on user may see all categories
            r = self.get_with_user(c.get_absolute_url(), 'zeus', 'zeus')
            self.assertEqual(r.status_code, 200)

    def test_forum_permission(self):
        for f in Forum.objects.all():
            r = self.get_with_user(f.get_absolute_url())
            self.assertEqual(r.status_code, 302 if f.hidden or f.category.hidden else 200)
            r = self.get_with_user(f.get_absolute_url(), 'zeus', 'zeus')
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.context['object_list'].count(), f.topics.filter(closed=False).count())

    def test_topic_permission(self):
        for t in Topic.objects.all():
            r = self.get_with_user(t.get_absolute_url())
            self.assertEqual(r.status_code, 302 if t.forum.hidden or t.forum.category.hidden else 200)
            r = self.get_with_user(t.get_absolute_url(), 'zeus', 'zeus')
            self.assertEqual(r.status_code, 200)

    def test_post_permission(self):
        for p in Post.objects.all():
            r = self.get_with_user(p.get_absolute_url())
            self.assertEqual(r.status_code, 302)
            r = self.get_with_user(p.get_absolute_url(), 'zeus', 'zeus')
            self.assertEqual(r.status_code, 302)

    def test_poll_add(self):
        add_topic_url = reverse('pybb:add_topic', kwargs={'forum_id': self.forum.id})
        self.login_client()
        response = self.client.get(add_topic_url)
        values = self.get_form_values(response)
        values['body'] = 'test poll body'
        values['name'] = 'test poll name'
        values['poll_type'] = 1 # poll_type = 1, create topic with poll
        values['poll_question'] = 'q1'
        values['poll_answers-0-text'] = 'answer1'
        values['poll_answers-1-text'] = 'answer2'
        values['poll_answers-TOTAL_FORMS'] = 2
        response = self.client.post(add_topic_url, values, follow=True)
        self.assertEqual(response.status_code, 200)
        new_topic = Topic.objects.get(name='test poll name')
        self.assertIsNone(new_topic.poll_question)
        self.assertFalse(PollAnswer.objects.filter(topic=new_topic).exists()) # no answers here


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
