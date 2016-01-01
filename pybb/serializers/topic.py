from rest_framework.serializers import ModelSerializer

from pybb.models import Topic
from pybb.serializers.post import PostSerializer


class TopicSerializer(ModelSerializer):

    class Meta:
        model = Topic
        fields = ('forum', 'name', 'created', 'user', 'views', 'sticky', 'closed', 'on_moderation', 'poll_type',
                  'poll_question', 'slug', 'posts')

    posts = PostSerializer(many=True)
