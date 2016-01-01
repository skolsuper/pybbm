from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings

from pybb import util
from pybb.models import Category, Forum, Topic, Post
from pybb.settings import settings as pybb_settings
from pybb.tests.utils import SharedTestModule

User = get_user_model()
Profile = util.get_pybb_profile_model()


class LogonRedirectTest(TestCase, SharedTestModule):
    """ test whether anonymous user gets redirected, whereas unauthorized user gets PermissionDenied """

    def setUp(self):
        # create users
        staff = User.objects.create_user('staff', 'staff@localhost', 'staff')
        staff.is_staff = True
        staff.save()
        nostaff = User.objects.create_user('nostaff', 'nostaff@localhost', 'nostaff')
        nostaff.is_staff = False
        nostaff.save()

        # create topic, post in hidden category
        self.category = Category(name='private', hidden=True)
        self.category.save()
        self.forum = Forum(name='priv1', category=self.category)
        self.forum.save()
        self.topic = Topic(name='a topic', forum=self.forum, user=staff)
        self.topic.save()
        self.post = Post(body='body post', topic=self.topic, user=staff, on_moderation=True)
        self.post.save()

    def test_redirect_category(self):
        # access without user should be redirected
        r = self.get_with_user(self.category.get_absolute_url())
        self.assertRedirects(r, settings.LOGIN_URL + '?next=%s' % self.category.get_absolute_url())
        # access with (unauthorized) user should get 403 (forbidden)
        r = self.get_with_user(self.category.get_absolute_url(), 'nostaff', 'nostaff')
        self.assertEquals(r.status_code, 403)
        # allowed user is allowed
        r = self.get_with_user(self.category.get_absolute_url(), 'staff', 'staff')
        self.assertEquals(r.status_code, 200)

    def test_redirect_forum(self):
        # access without user should be redirected
        r = self.get_with_user(self.forum.get_absolute_url())
        self.assertRedirects(r, settings.LOGIN_URL + '?next=%s' % self.forum.get_absolute_url())
        # access with (unauthorized) user should get 403 (forbidden)
        r = self.get_with_user(self.forum.get_absolute_url(), 'nostaff', 'nostaff')
        self.assertEquals(r.status_code, 403)
        # allowed user is allowed
        r = self.get_with_user(self.forum.get_absolute_url(), 'staff', 'staff')
        self.assertEquals(r.status_code, 200)

    def test_redirect_topic(self):
        # access without user should be redirected
        r = self.get_with_user(self.topic.get_absolute_url())
        self.assertRedirects(r, settings.LOGIN_URL + '?next=%s' % self.topic.get_absolute_url())
        # access with (unauthorized) user should get 403 (forbidden)
        r = self.get_with_user(self.topic.get_absolute_url(), 'nostaff', 'nostaff')
        self.assertEquals(r.status_code, 403)
        # allowed user is allowed
        r = self.get_with_user(self.topic.get_absolute_url(), 'staff', 'staff')
        self.assertEquals(r.status_code, 200)

    def test_redirect_post(self):
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
    def test_redirect_topic_add(self):
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

    def test_profile_autocreation_signal_on(self):
        user = User.objects.create_user('cronos', 'cronos@localhost', 'cronos')
        profile = getattr(user, pybb_settings.PYBB_PROFILE_RELATED_NAME, None)
        self.assertIsNotNone(profile)
        self.assertEqual(type(profile), util.get_pybb_profile_model())
        user.delete()

    def test_profile_autocreation_middleware(self):
        user = User.objects.create_user('cronos', 'cronos@localhost', 'cronos')
        getattr(user, pybb_settings.PYBB_PROFILE_RELATED_NAME).delete()
        #just display a page : the middleware should create the profile
        self.get_with_user('/', 'cronos', 'cronos')
        user = User.objects.get(username='cronos')
        profile = getattr(user, pybb_settings.PYBB_PROFILE_RELATED_NAME, None)
        self.assertIsNotNone(profile)
        self.assertEqual(type(profile), util.get_pybb_profile_model())
        user.delete()

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
