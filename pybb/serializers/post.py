# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.module_loading import import_string
from rest_framework import serializers

from pybb.models import Post
from pybb.settings import settings


class PostBodyField(serializers.CharField):

    def to_internal_value(self, data):
        for cleaner_path in settings.PYBB_BODY_CLEANERS:
            cleaner_fn = import_string(cleaner_path)
            data = cleaner_fn(data)
        return data


class PostSerializer(serializers.ModelSerializer):

    class Meta:
        model = Post
        fields = ('id', 'body', 'topic', 'user', 'user_ip', 'created', 'updated', 'on_moderation', 'attachment')

    body = PostBodyField()
