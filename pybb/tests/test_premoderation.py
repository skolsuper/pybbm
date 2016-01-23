from django.core import mail
from django.core.urlresolvers import reverse
from django.test import Client, override_settings
from rest_framework.test import APITestCase

from pybb.models import Post, Topic, Category, Forum
from pybb.tests.utils import User


@override_settings(PYBB_PREMODERATION=True)
class PreModerationTest(APITestCase):

    def setUp(self):
        mail.outbox = []

    def test_premoderation(self):
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(name='xfoo', description='bar', category=category)
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        topic = Topic.objects.create(name='etopic', forum=forum, user=user)

        self.client.force_authenticate(user)
        add_post_url = reverse('pybb:add_post')
        values = {
            'topic': topic.id,
            'body': 'test premoderation'
        }
        response = self.client.post(add_post_url, values)
        self.assertEqual(response.status_code, 201)
        post = Post.objects.get(body='test premoderation')
        self.assertEqual(post.on_moderation, True)

        # Post is visible by author
        response = self.client.get(post.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response.data['body'], 'test premoderation')

        # Post is not visible by anonymous user
        self.client.force_authenticate()
        response = self.client.get(post.get_absolute_url())
        self.assertEqual(response.status_code, 404)
        response = self.client.get(topic.get_absolute_url())
        self.assertNotContains(response, 'test premoderation')

        # But visible by superuser (with permissions)
        superuser = User.objects.create_superuser('admin', 'admin@localhost', 'admin')
        self.client.force_authenticate(superuser)
        response = self.client.get(post.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response.data['body'], 'test premoderation')

    def test_superuser_premoderation(self):
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(name='xfoo', description='bar', category=category)
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        topic = Topic.objects.create(name='etopic', forum=forum, user=user)

        add_post_url = reverse('pybb:add_post')
        values = {
            'topic': topic.id,
            'body': 'test premoderation'
        }
        superuser = User.objects.create_superuser('admin', 'admin@localhost', 'admin')
        self.client.force_authenticate(superuser)
        response = self.client.post(add_post_url, values)
        self.assertEqual(response.status_code, 201)
        post = Post.objects.get(body='test premoderation staff')
        self.assertFalse(post.on_moderation)

        self.client.force_authenticate()
        response = self.client.get(post.get_absolute_url())
        self.assertContains(response.data['body'], 'test premoderation staff')

    def test_moderation(self):
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(name='xfoo', description='bar', category=category)
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        topic = Topic.objects.create(name='etopic', forum=forum, user=user)

        self.client.force_authenticate(user)
        add_post_url = reverse('pybb:add_post')
        values = {
            'topic': topic.id,
            'body': 'test premoderation'
        }
        self.client.post(add_post_url, values)
        post = Post.objects.get(topic=topic, body='test premoderation')
        self.assertTrue(post.on_moderation)

        superuser = User.objects.create_superuser('admin', 'admin@localhost', 'admin')
        self.client.force_authenticate(superuser)

        # Superuser can moderate
        moderate_url = reverse('pybb:moderate_post', kwargs={'pk': post.id})
        response = self.client.get(moderate_url)
        self.assertEqual(response.status_code, 405, 'Moderation requires a POST request.')

        response = self.client.post(moderate_url)
        self.assertEqual(response.status_code, 200)
        post.refresh_from_db()
        self.assertFalse(post.on_moderation)

        # Now all can see this post:
        self.client.force_authenticate()
        response = self.client.get(post.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response.data['body'], 'test premoderation')

        # Other users can't moderate
        post.on_moderation = True
        post.save()
        self.client.force_authenticate(user)
        response = self.client.post(moderate_url)
        self.assertEqual(response.status_code, 403)

    def test_topic_moderation(self):
        # If user create new topic it goes to moderation if MODERATION_ENABLE
        # When first post is moderated, topic becomes moderated too
        self.client.login(username='zeus', password='zeus')
        add_topic_url = reverse('pybb:add_topic', kwargs={'forum_id': self.forum.id})
        response = self.client.get(add_topic_url)
        values = self.get_form_values(response)
        values['body'] = 'new topic test'
        values['name'] = 'new topic name'
        values['poll_type'] = 0
        response = self.client.post(add_topic_url, values, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'new topic test')

        client = Client()
        response = client.get(self.forum.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'new topic name')
        response = client.get(Topic.objects.get(name='new topic name').get_absolute_url())
        self.assertEqual(response.status_code, 302)
        response = admin_client.get(reverse('pybb:moderate_post',
                                            kwargs={'pk': Post.objects.get(body='new topic test').id}),
                                    follow=True)
        self.assertEqual(response.status_code, 200)

        response = client.get(self.forum.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'new topic name')
        response = client.get(Topic.objects.get(name='new topic name').get_absolute_url())
        self.assertEqual(response.status_code, 200)


