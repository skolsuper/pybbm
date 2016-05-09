# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ParseError
from rest_framework.generics import DestroyAPIView, UpdateAPIView, RetrieveAPIView, ListCreateAPIView
from rest_framework.response import Response

from pybb.models import Topic, Post
from pybb.pagination import PybbPostPagination
from pybb.permissions import PermissionsMixin
from pybb.read_tracking import mark_read
from pybb.serializers import PostSerializer
from pybb.settings import settings
from pybb.subscription import notify_topic_subscribers

User = get_user_model()
username_field = User.USERNAME_FIELD


class ListCreatePostView(PermissionsMixin, ListCreateAPIView):

    queryset = Post.objects.all()
    serializer_class = PostSerializer
    pagination_class = PybbPostPagination

    def get_topic(self):
        topic_pk = self.request.query_params.get('topic', None)
        if topic_pk is not None:
            if not hasattr(self, '_topic'):
                qs = Topic.objects.all()
                self._topic = get_object_or_404(self.perms.filter_topics(self.request.user, qs), pk=topic_pk)
            return self._topic

    def get_queryset(self):
        qs = self.perms.filter_posts(self.request.user, self.queryset)
        topic = self.get_topic()
        if topic is not None:
            qs = qs.filter(topic=topic)
        return qs

    def get_paginated_response(self, data):
        response = super(ListCreatePostView, self).get_paginated_response(data)
        topic = self.get_topic()
        if data and self.request.user.is_authenticated() and topic is not None:
            last_read_time = data.serializer.instance[-1].created
            mark_read(self.request.user, topic, last_read_time)
        return response

    def create(self, request, *args, **kwargs):
        try:
            topics = self.perms.filter_topics(self.request.user, Topic.objects.all())
            topic = topics.get(pk=request.data['topic'])
        except Topic.DoesNotExist:
            raise ParseError(_('Specified topic not found.'))
        if not self.perms.may_create_post(request.user, topic):
            self.permission_denied(request, _('You do not have permission to post in this topic'))

        post_data = request.data.copy()
        if request.user.is_authenticated():
            post_data['user'] = request.user.id

        post_data['user_ip'] = request.META['REMOTE_ADDR']
        post_data['on_moderation'] = not self.perms.may_create_post_unmoderated(request.user, topic)
        serializer = self.get_serializer(data=post_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        if request.user.is_authenticated():
            mark_read(user=request.user, topic=topic, last_read_time=now())
        if not settings.PYBB_DISABLE_NOTIFICATIONS:
            notify_topic_subscribers(serializer.instance, current_site=get_current_site(request))
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class UpdatePostView(PermissionsMixin, UpdateAPIView):

    queryset = Post.objects.all()
    serializer_class = PostSerializer

    def get_object(self):
        post = super(UpdatePostView, self).get_object()
        if not self.perms.may_edit_post(self.request.user, post):
            raise PermissionDenied
        return post

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data
        data['updated'] = now()
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


class PostView(PermissionsMixin, RetrieveAPIView):

    queryset = Post.objects.all()
    serializer_class = PostSerializer

    def get_queryset(self):
        return self.perms.filter_posts(self.request.user, self.queryset)

    def get_object(self):
        post = super(PostView, self).get_object()
        if not self.perms.may_view_post(self.request.user, post):
            raise PermissionDenied
        return post


class DeletePostView(PermissionsMixin, DestroyAPIView):

    def get_object(self, queryset=None):
        post = get_object_or_404(Post.objects.select_related('topic', 'topic__forum'), pk=self.kwargs['pk'])
        if not self.perms.may_delete_post(self.request.user, post):
            raise PermissionDenied
        topic = post.topic
        if not self.perms.may_moderate_topic(self.request.user, topic):
            raise PermissionDenied
        return post

    def perform_destroy(self, instance):
        if instance.topic.head == instance:
            instance.topic.delete()
        else:
            instance.delete()

