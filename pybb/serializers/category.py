# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import serializers

from pybb.models import Category
from pybb.serializers.forum import ForumSerializer


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = ('id', 'name', 'position', 'hidden', 'slug', 'forums')
        depth = 1

    forums = ForumSerializer(read_only=True, many=True)
