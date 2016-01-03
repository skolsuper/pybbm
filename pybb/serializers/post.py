# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from rest_framework import serializers

from pybb.models import Post, Attachment


class PostSerializer(serializers.ModelSerializer):

    class Meta:
        model = Post
        fields = ('body', 'topic', 'user', 'user_ip', 'created', 'updated', 'on_moderation', 'attachment',
                  'attachment_url')

    attachment = serializers.FileField(required=False, write_only=True)
    attachment_url = serializers.URLField(read_only=True, allow_blank=True, source='attachment.file.url')

    def save(self, **kwargs):
        attachment = self.validated_data.pop('attachment', None)
        post = super(PostSerializer, self).save(**kwargs)
        if attachment is not None:
            Attachment.objects.create(post=post, file=attachment)
        return post
