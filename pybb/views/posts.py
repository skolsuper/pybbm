# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied, ParseError
from rest_framework.generics import DestroyAPIView, CreateAPIView, UpdateAPIView, RetrieveAPIView
from rest_framework.response import Response

from pybb.models import Topic, Post
from pybb.permissions import PermissionsMixin, get_perms
from pybb.serializers import PostSerializer

User = get_user_model()
username_field = User.USERNAME_FIELD


class CreatePostView(PermissionsMixin, CreateAPIView):

    serializer_class = PostSerializer

    def get_queryset(self):
        return self.perms.filter_topics(self.request.user, Topic.objects.all())

    def create(self, request, *args, **kwargs):
        try:
            topic = self.get_queryset().get(pk=request.data['topic'])
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

    def get_queryset(self):
        return self.perms.filter_posts(self.request.user, self.queryset)

    def get_object(self):
        post = super(PostView, self).get_object()
        if not self.perms.may_view_post(self.request.user, post):
            raise PermissionDenied
        return post


@api_view(['POST'])
def moderate_post(request, *args, **kwargs):
    post = get_object_or_404(Post, pk=kwargs['pk'])
    if not get_perms().may_moderate_topic(request.user, post.topic):
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

    def perform_destroy(self, instance):
        if instance.topic.head == instance:
            instance.topic.delete()
        else:
            instance.delete()

