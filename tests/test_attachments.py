# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from tempfile import NamedTemporaryFile

import pytest
from django.core.urlresolvers import reverse

from pybb.models import Post, Category, Forum, Topic


@pytest.mark.django_db
def test_attachments(settings, django_user_model, api_client):
    settings.PYBB_ATTACHMENT_ENABLE = True
    settings.PYBB_PREMODERATION = False
    user = django_user_model.objects.create_user('zeus', 'zeus@localhost', 'zeus')
    category = Category.objects.create(name='foo')
    forum = Forum.objects.create(name='xfoo', description='bar', category=category)
    topic = Topic.objects.create(name='etopic', forum=forum, user=user)
    add_post_url = reverse('pybb:post_list')
    api_client.force_authenticate(user)
    with NamedTemporaryFile() as fp:
        fp.write(b'hello')
        fp.seek(0)
        values = {'topic': topic.id, 'body': 'test attachment', 'attachment': fp}
        response = api_client.post(add_post_url, values, format='multipart')
        assert response.status_code == 201
        assert 'attachment' in response.data
        post = Post.objects.get(body='test attachment')
        assert post.attachment is not None

        # cleanup
        post.attachment.delete()
