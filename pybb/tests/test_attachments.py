# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os

from django.core.urlresolvers import reverse
from django.test import override_settings
from rest_framework.test import APITestCase

from pybb.models import Post, Category, Forum, Topic
from pybb.tests.utils import User

FILE_NAME = os.path.join(os.path.dirname(__file__), '../static', 'pybb', 'img', 'attachment.png')


@override_settings(PYBB_ATTACHMENT_ENABLE=True, PYBB_PREMODERATION=False)
class AttachmentTest(APITestCase):

    def test_attachments(self):
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(name='xfoo', description='bar', category=category)
        topic = Topic.objects.create(name='etopic', forum=forum, user=user)
        add_post_url = reverse('pybb:add_post')
        self.client.force_authenticate(user)
        with open(FILE_NAME, 'rb') as fp:
            values = {'topic': topic.id, 'body': 'test attachment', 'attachment': fp}
            response = self.client.post(add_post_url, values, format='multipart')
        self.assertEqual(response.status_code, 201)
        self.assertIn('attachment', response.data)
        post = Post.objects.get(body='test attachment')
        self.assertIsNotNone(post.attachment)

        # cleanup
        post.attachment.delete()
