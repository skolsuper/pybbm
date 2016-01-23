from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from rest_framework.test import APITestCase

from pybb.models import Post, Category, Forum, Topic

User = get_user_model()


class FiltersTest(APITestCase):

    def test_filters(self):
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(name='xfoo', description='bar', category=category)
        topic = Topic.objects.create(name='etopic', forum=forum, user=user)
        add_post_url = reverse('pybb:add_post')
        self.client.force_authenticate(user)
        values = {
            'topic': topic.id,
            'body': 'test\n \n \n\nmultiple empty lines\n'
        }
        response = self.client.post(add_post_url, values, follow=True)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Post.objects.all()[0].body, 'test<br />multiple empty lines')
