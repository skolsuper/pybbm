# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.generics import DestroyAPIView, CreateAPIView, UpdateAPIView, RetrieveAPIView
from rest_framework.response import Response

from pybb import settings as defaults, util
from pybb.models import Forum, Topic, Post
from pybb.permissions import PermissionsMixin
from pybb.serializers import PostSerializer

User = get_user_model()
username_field = User.USERNAME_FIELD


class CreatePostView(PermissionsMixin, CreateAPIView):

    serializer_class = PostSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        if not (request.user.is_authenticated() or defaults.settings.PYBB_ENABLE_ANONYMOUS_POST):
            raise PermissionDenied

        if 'forum_id' in kwargs:
            forum = get_object_or_404(self.perms.filter_forums(request.user, Forum.objects.all()), pk=kwargs['forum_id'])
            if not self.perms.may_create_topic(request.user, forum):
                raise PermissionDenied
        elif 'topic_id' in kwargs:
            topic = get_object_or_404(self.perms.filter_topics(request.user, Topic.objects.all()), pk=kwargs['topic_id'])
            if not self.perms.may_create_post(request.user, topic):
                raise PermissionDenied

            if 'quote_id' in request.query_params:
                try:
                    quote_id = int(request.query_params.get('quote_id'))
                except TypeError:
                    raise Http404
                else:
                    post = get_object_or_404(Post, pk=quote_id)
                    if not self.perms.may_view_post(request.user, post):
                        raise PermissionDenied
                    profile = util.get_pybb_profile(post.user)
                    data['quote'] = util._get_markup_quoter(defaults.settings.PYBB_MARKUP)(post.body, profile.get_display_name())

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
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


class PostView(PermissionsMixin, RetrieveAPIView):

    queryset = Post.objects.all()
    serializer_class = PostSerializer

    def get_object(self):
        post = super(PostView, self).get_object()
        if not self.perms.may_view_post(self.request.user, post):
            raise PermissionDenied
        return post


@api_view
def moderate_post(self, request, *args, **kwargs):
    post = get_object_or_404(Post, pk=kwargs['pk'])
    if not self.perms.may_moderate_topic(request.user, post.topic):
        raise PermissionDenied
    post.on_moderation = False
    post.save()
    headers = {'Location': post.get_absolute_url()}
    return Response(status=status.HTTP_200_OK, headers=headers)


class DeletePostView(PermissionsMixin, DestroyAPIView):

    def get_object(self, queryset=None):
        post = get_object_or_404(Post.objects.select_related('topic', 'topic__forum'), pk=self.kwargs['pk'])
        if not self.perms.may_delete_post(self.request.user, post):
            raise PermissionDenied
        topic = post.topic
        if not self.perms.may_moderate_topic(self.request.user, topic):
            raise PermissionDenied
        return post
