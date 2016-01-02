from rest_framework import serializers

from pybb.models import Category


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = ('name', 'position', 'hidden', 'slug')
