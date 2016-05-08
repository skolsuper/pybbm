# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
from django.db.models import Max
from rest_framework import serializers

from pybb.models import Forum, Post, ForumReadTracker


class ForumSerializer(serializers.ModelSerializer):

    class Meta:
        model = Forum
        fields = ('id', 'category', 'parent', 'name', 'position', 'description', 'moderators', 'hidden', 'headline',
                  'slug', 'unread')

    unread = serializers.SerializerMethodField()

    def get_unread(self, forum):
        user = self.context['request'].user
        if user.is_anonymous():
            return False

        last_updated = Post.objects.filter(topic__forum=forum).aggregate(Max('created'))['created__max']
        if last_updated is None:
            return False

        last_updated -= datetime.timedelta(seconds=0.1)  # Fuzzing factor to account for timing differences between auto_now and auto_now_add fields.
        return not ForumReadTracker.objects.filter(user=user, forum=forum, time_stamp__gte=last_updated).exists()
