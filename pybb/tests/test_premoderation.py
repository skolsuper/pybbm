from django.core.urlresolvers import reverse
from django.test import override_settings
from rest_framework.test import APITestCase

from pybb.models import Post, Topic, Category, Forum
from pybb.tests.utils import User


@override_settings(PYBB_PREMODERATION=True)
class PreModerationTest(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(PreModerationTest, cls).setUpClass()
        cls.category = Category.objects.create(name='foo')
        cls.forum = Forum.objects.create(name='xfoo', description='bar', category=cls.category)
        cls.user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        cls.topic = Topic.objects.create(name='etopic', forum=cls.forum, user=cls.user)

    @classmethod
    def tearDownClass(cls):
        cls.category.delete()
        cls.user.delete()
        super(PreModerationTest, cls).tearDownClass()

    def test_premoderation(self):
        self.client.force_authenticate(self.user)
        add_post_url = reverse('pybb:add_post')
        values = {
            'topic': self.topic.id,
            'body': 'test premoderation'
        }
        response = self.client.post(add_post_url, values)
        self.assertEqual(response.status_code, 201)
        post = Post.objects.get(body='test premoderation')
        self.assertEqual(post.on_moderation, True)

        # Post is visible by author
        response = self.client.get(post.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['body'], 'test premoderation')

        # Post is not visible by anonymous user
        self.client.force_authenticate()
        response = self.client.get(post.get_absolute_url())
        self.assertEqual(response.status_code, 404)
        response = self.client.get(self.topic.get_absolute_url())
        self.assertNotContains(response, 'test premoderation')

        # But visible by superuser (with permissions)
        superuser = User.objects.create_superuser('admin', 'admin@localhost', 'admin')
        self.client.force_authenticate(superuser)
        response = self.client.get(post.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['body'], 'test premoderation')

    def test_superuser_premoderation(self):
        add_post_url = reverse('pybb:add_post')
        values = {
            'topic': self.topic.id,
            'body': 'test premoderation staff'
        }
        superuser = User.objects.create_superuser('admin', 'admin@localhost', 'admin')
        self.client.force_authenticate(superuser)
        response = self.client.post(add_post_url, values)
        self.assertEqual(response.status_code, 201)
        post = Post.objects.get(body='test premoderation staff')
        self.assertFalse(post.on_moderation)

        self.client.force_authenticate()
        response = self.client.get(post.get_absolute_url())
        self.assertEqual(response.data['body'], 'test premoderation staff')

    def test_moderation(self):
        self.client.force_authenticate(self.user)
        add_post_url = reverse('pybb:add_post')
        values = {
            'topic': self.topic.id,
            'body': 'test premoderation'
        }
        self.client.post(add_post_url, values)
        post = Post.objects.get(topic=self.topic, body='test premoderation')
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
        self.assertEqual(response.data['body'], 'test premoderation')

        # Other users can't moderate
        post.on_moderation = True
        post.save()
        self.client.force_authenticate(self.user)
        response = self.client.post(moderate_url)
        self.assertEqual(response.status_code, 403)

    def test_topic_moderation(self):
        add_topic_url = reverse('pybb:topic_list')
        values = {
            'forum': self.forum.id,
            'body': 'new topic test',
            'name': 'new topic name',
            'poll_type': Topic.POLL_TYPE_NONE
        }
        self.client.force_authenticate(self.user)
        response = self.client.post(add_topic_url, values)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['name'], 'new topic name')

        # self.client.force_authenticate()
        # response = self.client.get(add_topic_url)  # Topic list URL is same as topic create
        # self.assertEqual(response.status_code, 200)
        # self.assertNotContains(response.data['results'], 'new topic name')
        # response = client.get(Topic.objects.get(name='new topic name').get_absolute_url())
        # self.assertEqual(response.status_code, 302)
        # response = admin_client.get(reverse('pybb:moderate_post',
        #                                     kwargs={'pk': Post.objects.get(body='new topic test').id}),
        #                             follow=True)
        # self.assertEqual(response.status_code, 200)
        #
        # response = client.get(self.forum.get_absolute_url())
        # self.assertEqual(response.status_code, 200)
        # self.assertContains(response, 'new topic name')
        # response = client.get(Topic.objects.get(name='new topic name').get_absolute_url())
        # self.assertEqual(response.status_code, 200)
