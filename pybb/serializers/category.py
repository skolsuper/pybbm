from rest_framework import serializers

from pybb.models import Category
from pybb.serializers.forum import ForumSerializer


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = ('name', 'position', 'hidden', 'slug', 'forums')
        depth = 1

    forums = ForumSerializer(read_only=True, many=True)
