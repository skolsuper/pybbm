# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os

from django.core.urlresolvers import reverse
from django.test import override_settings
from rest_framework.test import APITestCase

from pybb.models import Post
from pybb.tests.utils import SharedTestModule

FILE_NAME = os.path.join(os.path.dirname(__file__), '../static', 'pybb', 'img', 'attachment.png')


@override_settings(PYBB_ATTACHMENT_ENABLE=True, PYBB_PREMODERATION=False)
class AttachmentTest(APITestCase, SharedTestModule):
    def setUp(self):
        self.create_user()
        self.create_initial()

    def test_attachments(self):
        add_post_url = reverse('pybb:add_post')
        self.client.force_authenticate(self.user)
        with open(FILE_NAME, 'rb') as fp:
            values = {'topic': self.topic.id, 'body': 'test attachment', 'attachment': fp}
            response = self.client.post(add_post_url, values, follow=True)
        self.assertEqual(response.status_code, 201)
        self.assertIn('attachment', response.data)
        post = Post.objects.get(body='test attachment')
        self.assertIsNotNone(post.attachment)
