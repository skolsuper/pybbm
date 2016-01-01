from rest_framework.serializers import ModelSerializer

from pybb.models import Post


class PostSerializer(ModelSerializer):

    class Meta:
        model = Post
        fields = ('body', 'topic', 'user', 'created', 'updated', 'on_moderation')
