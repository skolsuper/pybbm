# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os

from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.test import TestCase, override_settings

from pybb.models import Post
from pybb.tests.utils import SharedTestModule


@override_settings(PYBB_ATTACHMENT_ENABLE=True, PYBB_PREMODERATION=False)
class AttachmentTest(TestCase, SharedTestModule):
    def setUp(self):
        self.file_name = os.path.join(os.path.dirname(__file__), '../static', 'pybb', 'img', 'attachment.png')
        self.create_user()
        self.create_initial()

    def test_attachment_one(self):
        add_post_url = reverse('pybb:add_post', kwargs={'topic_id': self.topic.id})
        self.login_client()
        response = self.client.get(add_post_url)
        with open(self.file_name, 'rb') as fp:
            values = self.get_form_values(response)
            values['body'] = 'test attachment'
            values['attachments-0-file'] = fp
            response = self.client.post(add_post_url, values, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Post.objects.filter(body='test attachment').exists())

    def test_attachment_two(self):
        add_post_url = reverse('pybb:add_post', kwargs={'topic_id': self.topic.id})
        self.login_client()
        response = self.client.get(add_post_url)
        with open(self.file_name, 'rb') as fp:
            values = self.get_form_values(response)
            values['body'] = 'test attachment'
            values['attachments-0-file'] = fp
            del values['attachments-INITIAL_FORMS']
            del values['attachments-TOTAL_FORMS']
            with self.assertRaises(ValidationError):
                self.client.post(add_post_url, values, follow=True)
