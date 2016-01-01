from rest_framework import serializers

from pybb.models import Forum


class ForumSerializer(serializers.ModelSerializer):

    class Meta:
        model = Forum
        fields = ('category', 'parent', 'name', 'position', 'description', 'moderators', 'hidden', 'readed_by',
                  'headline', 'slug')
