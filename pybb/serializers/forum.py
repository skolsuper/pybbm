# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import serializers

from pybb.models import Forum


class ForumSerializer(serializers.ModelSerializer):

    class Meta:
        model = Forum
        fields = ('id', 'category', 'parent', 'name', 'position', 'description', 'moderators', 'hidden', 'headline', 'slug')
