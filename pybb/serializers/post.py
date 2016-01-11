# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import serializers

from pybb.models import Post
from pybb.settings import settings
from pybb.util import resolve_function, resolve_class


class PostBodyField(serializers.CharField):

    def to_internal_value(self, data):
        for cleaner_path in settings.PYBB_BODY_CLEANERS:
            cleaner_fn = resolve_function(cleaner_path)
            data = cleaner_fn(data)
        return data

    def to_representation(self, value):
        markup_engine_path = settings.PYBB_MARKUP_ENGINES_PATHS[settings.PYBB_MARKUP]
        markup_engine = resolve_class(markup_engine_path)
        return markup_engine.format(value)


class PostSerializer(serializers.ModelSerializer):

    class Meta:
        model = Post
        fields = ('id', 'body', 'topic', 'user', 'user_ip', 'created', 'updated', 'on_moderation', 'attachment')

    body = PostBodyField()
