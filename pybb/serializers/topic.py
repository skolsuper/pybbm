from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from pybb import compat
from pybb.models import Topic


class DefaultSlugBuilder(object):

    def __call__(self):
        return self.slug or compat.slugify(self.name)

    def set_context(self, field):
        self.slug = field.parent.initial_data.get('slug', None)
        self.name = field.parent.initial_data.get('name', None)


class TopicSerializer(serializers.ModelSerializer):

    class Meta:
        model = Topic
        fields = ('forum', 'name', 'created', 'user', 'views', 'sticky', 'closed', 'on_moderation', 'poll_type',
                  'poll_question', 'slug')

    slug = serializers.SlugField(max_length=255, required=False, default=DefaultSlugBuilder())

    def run_validators(self, value, unique_slug_fail_count=0):
        try:
            return super(TopicSerializer, self).run_validators(value)
        except ValidationError:
            if unique_slug_fail_count != 0:
                num_chars = len(str(unique_slug_fail_count)) + 1
                value['slug'] = value['slug'][:-num_chars]
            unique_slug_fail_count += 1
            value['slug'] += '-{}'.format(unique_slug_fail_count)
            return self.run_validators(value, unique_slug_fail_count)
