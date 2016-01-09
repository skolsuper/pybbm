# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import serializers

from pybb.models import Post


class PostSerializer(serializers.ModelSerializer):

    class Meta:
        model = Post
        fields = ('id', 'body', 'topic', 'user', 'user_ip', 'created', 'updated', 'on_moderation', 'attachment')
