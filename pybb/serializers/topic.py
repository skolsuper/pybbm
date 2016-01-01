from rest_framework.serializers import ModelSerializer

from pybb.models import Topic


class TopicSerializer(ModelSerializer):

    class Meta:
        model = Topic
        fields = ('forum', 'name', 'created', 'user', 'views', 'sticky', 'closed', 'on_moderation', 'poll_type',
                  'poll_question', 'slug')
