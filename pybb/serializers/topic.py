# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from pybb import compat
from pybb.models import Topic, Post
from pybb.settings import settings


class DefaultSlugBuilder(object):

    def __call__(self):
        return self.slug or compat.slugify(self.name)

    def set_context(self, field):
        self.slug = field.parent.initial_data.get('slug', None)
        self.name = field.parent.initial_data.get('name', None)


class TopicSerializer(serializers.ModelSerializer):

    class Meta:
        model = Topic
        fields = ('id', 'forum', 'name', 'body', 'created', 'user', 'views', 'sticky', 'closed', 'on_moderation', 'poll_type',
                  'poll_question', 'slug')
        extra_kwargs = {
            'user': {'allow_null': True}
        }

    body = serializers.CharField(required=True, write_only=True)
    slug = serializers.SlugField(max_length=255, required=False, default=DefaultSlugBuilder())

    def save(self, **kwargs):
        post_body = self.validated_data.pop('body')
        instance = super(TopicSerializer, self).save(**kwargs)
        Post.objects.create(topic=instance, user=instance.user, body=post_body, on_moderation=instance.on_moderation)
        return instance

    def run_validators(self, value, unique_slug_fail_count=0):
        try:
            return super(TopicSerializer, self).run_validators(value)
        except ValidationError:
            if unique_slug_fail_count != 0:
                num_chars = len(str(unique_slug_fail_count)) + 1
                value['slug'] = value['slug'][:-num_chars]
            if unique_slug_fail_count == settings.PYBB_NICE_URL_SLUG_DUPLICATE_LIMIT:
                msg = _('After {limit} attempts, there is not any unique slug value for "{slug}"')
                raise ValidationError(msg.format(limit=settings.PYBB_NICE_URL_SLUG_DUPLICATE_LIMIT, slug=value['slug']))
            unique_slug_fail_count += 1
            value['slug'] += '-{}'.format(unique_slug_fail_count)
            return self.run_validators(value, unique_slug_fail_count)
