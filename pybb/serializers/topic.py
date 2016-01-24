# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from pybb import compat
from pybb.models import Topic, Post, PollAnswer, TopicReadTracker, ForumReadTracker
from pybb.serializers.post import PostBodyField
from pybb.settings import settings


class DefaultSlugBuilder(object):

    def __call__(self):
        return self.slug or compat.slugify(self.name)

    def set_context(self, field):
        self.slug = field.parent.initial_data.get('slug', None)
        self.name = field.parent.initial_data.get('name', None)


class PollAnswerSerializer(serializers.Serializer):

    text = serializers.CharField()
    votes = serializers.IntegerField(read_only=True)
    votes_percent = serializers.FloatField(read_only=True)

    @property
    def data(self):
        return super(PollAnswerSerializer, self).data()
    
    def validate(self, attrs):
        return super(PollAnswerSerializer, self).validate(attrs)
    
    def to_internal_value(self, data):
        return super(PollAnswerSerializer, self).to_internal_value(data)

    @classmethod
    def many_init(cls, *args, **kwargs):
        return super(PollAnswerSerializer, cls).many_init(*args, **kwargs)


class TopicSerializer(serializers.ModelSerializer):

    class Meta:
        model = Topic
        fields = ('id', 'forum', 'name', 'body', 'created', 'user', 'views', 'sticky', 'closed', 'on_moderation',
                  'poll_type', 'poll_question', 'poll_answers', 'slug', 'unread')
        extra_kwargs = {
            'user': {'allow_null': True}
        }

    body = PostBodyField(required=True, write_only=True)
    slug = serializers.SlugField(max_length=255, required=False, default=DefaultSlugBuilder())
    poll_answers = PollAnswerSerializer(many=True, required=False)
    unread = serializers.SerializerMethodField()

    def get_unread(self, topic):
        user = self.context['request'].user
        if user.is_anonymous():
            return False

        last_topic_update = topic.updated or topic.created

        unread = not ForumReadTracker.objects.filter(
            forum=topic.forum,
            user=user.id,
            time_stamp__gte=last_topic_update).exists()
        unread &= not TopicReadTracker.objects.filter(
            topic=topic,
            user=user.id,
            time_stamp__gte=last_topic_update).exists()
        return unread

    def validate(self, attrs):
        num_answers = len(attrs.get('poll_answers', []))
        if 'poll_type' not in attrs or attrs['poll_type'] == Topic.POLL_TYPE_NONE:
            if num_answers > 0:
                raise ValidationError(_('Poll type none selected but poll answers provided.'))
        else:
            if num_answers == 0:
                raise ValidationError(_('Poll selected but no answers provided.'))
            elif num_answers > settings.PYBB_POLL_MAX_ANSWERS:
                raise ValidationError(
                    _('More than the maximum of {} answers provided'.format(settings.PYBB_POLL_MAX_ANSWERS)))
        return attrs

    def save(self, **kwargs):
        post_body = self.validated_data.pop('body')
        poll_answers = self.validated_data.pop('poll_answers', [])
        instance = super(TopicSerializer, self).save(**kwargs)
        for answer in poll_answers:
            PollAnswer.objects.create(topic=instance, text=answer['text'])
        Post.objects.create(
            topic=instance,
            user=instance.user,
            user_ip=self.context['request'].META['REMOTE_ADDR'],
            body=post_body,
            on_moderation=instance.on_moderation
        )
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
