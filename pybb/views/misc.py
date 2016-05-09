# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, get_list_or_404
from django.utils import timezone
from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import permission_classes, api_view
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.generics import CreateAPIView, GenericAPIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from pybb.models import Forum, Topic, Post, TopicReadTracker, ForumReadTracker, PollAnswerUser, PollAnswer
from pybb.permissions import get_perms, PermissionsMixin
from pybb.serializers import TopicSerializer
from pybb.settings import settings

User = get_user_model()
username_field = User.USERNAME_FIELD


class TopicActionBaseView(PermissionsMixin, GenericAPIView):
    serializer_class = TopicSerializer

    def get_object(self):
        return get_object_or_404(Topic, pk=self.kwargs['pk'])

    def post(self, *args, **kwargs):
        topic = self.get_object()
        self.action(topic)
        serializer = self.get_serializer(topic)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def action(self, topic):
        raise NotImplementedError


class StickTopicView(TopicActionBaseView):

    def action(self, topic):
        if not self.perms.may_stick_topic(self.request.user, topic):
            raise PermissionDenied
        topic.sticky = True
        topic.save()


class UnstickTopicView(TopicActionBaseView):

    def action(self, topic):
        if not self.perms.may_unstick_topic(self.request.user, topic):
            raise PermissionDenied
        topic.sticky = False
        topic.save()


class CloseTopicView(TopicActionBaseView):

    def action(self, topic):
        if not self.perms.may_close_topic(self.request.user, topic):
            raise PermissionDenied
        topic.closed = True
        topic.save()


class OpenTopicView(TopicActionBaseView):
    def action(self, topic):
        if not self.perms.may_open_topic(self.request.user, topic):
            raise PermissionDenied
        topic.closed = False
        topic.save()


class TopicPollVoteView(PermissionsMixin, CreateAPIView):

    permission_classes = (IsAuthenticated,)
    queryset = Topic.objects.exclude(poll_type=Topic.POLL_TYPE_NONE)

    def post(self, request, *args, **kwargs):
        topic = self.get_object()
        if not self.perms.may_vote_in_topic(self.request.user, topic):
            raise PermissionDenied

        answers = get_list_or_404(PollAnswer, topic=topic, pk__in=request.data['answers'])
        poll_answer_objects = [PollAnswerUser(poll_answer=answer, user=self.request.user) for answer in answers]
        PollAnswerUser.objects.bulk_create(poll_answer_objects)
        serializer = TopicSerializer(topic, context=self.get_serializer_context())
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_object(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def topic_cancel_poll_vote(request, pk):
    topic = get_object_or_404(Topic, pk=pk)
    PollAnswerUser.objects.filter(user=request.user, poll_answer__topic_id=topic.id).delete()
    serializer = TopicSerializer(topic, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def delete_subscription(request, pk):
    perms = get_perms()
    topic = get_object_or_404(perms.filter_topics(request.user, Topic.objects.all()), pk=pk)
    topic.subscribers.remove(request.user)
    serializer = TopicSerializer(topic, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_subscription(request, pk):
    if settings.PYBB_DISABLE_SUBSCRIPTIONS:
        raise NotFound
    perms = get_perms()
    topic = get_object_or_404(perms.filter_topics(request.user, Topic.objects.all()), pk=pk)
    if not perms.may_subscribe_topic(request.user, topic):
        raise PermissionDenied
    topic.subscribers.add(request.user)
    serializer = TopicSerializer(topic, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_as_read(request):
    perms = get_perms()
    for forum in perms.filter_forums(request.user, Forum.objects.all()):
        forum_mark, new = ForumReadTracker.objects.get_or_create(forum=forum, user=request.user)
        forum_mark.time_stamp = timezone.now()
        forum_mark.save()
    TopicReadTracker.objects.filter(user=request.user).delete()
    msg = _('All forums marked as read')
    return Response({'message': msg}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def block_user(request, username):
    perms = get_perms()
    user = get_object_or_404(User, **{username_field: username})
    if not perms.may_block_user(request.user, user):
        raise PermissionDenied
    user.is_active = False
    user.save()
    if 'block_and_delete_messages' in request.data:
        Post.objects.filter(user=user).delete()
        Topic.objects.filter(user=user).delete()

    msg = _('User {} successfully blocked'.format(user.username))
    return Response({'message': msg}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def unblock_user(request, username):
    perms = get_perms()
    user = get_object_or_404(User, **{username_field: username})
    if not perms.may_block_user(request.user, user):
        raise PermissionDenied
    user.is_active = True
    user.save()
    msg = _('User {} successfully unblocked'.format(user.username))
    return Response({'message': msg}, status=status.HTTP_200_OK)


@api_view(['POST'])
def moderate_post(request, *args, **kwargs):
    post = get_object_or_404(Post, pk=kwargs['pk'])
    if not get_perms().may_moderate_topic(request.user, post.topic):
        raise PermissionDenied
    post.on_moderation = False
    post.save()
    headers = {'Location': post.get_absolute_url()}
    return Response(status=status.HTTP_200_OK, headers=headers)


@api_view(['POST'])
def moderate_topic(request, *args, **kwargs):
    topic = get_object_or_404(Topic, pk=kwargs['pk'])
    if not get_perms().may_moderate_forum(request.user, topic.forum):
        raise PermissionDenied
    topic.on_moderation = False
    topic.save()
    topic.posts.update(on_moderation=False)
    headers = {'Location': topic.get_absolute_url()}
    return Response(status=status.HTTP_200_OK, headers=headers)
