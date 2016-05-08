# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.generics import RetrieveAPIView, ListAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated

from pybb import util
from pybb.models import Topic, Post
from pybb.pagination import PybbPostPagination, PybbTopicPagination
from pybb.permissions import PermissionsMixin
from pybb.serializers import ProfileSerializer, PostSerializer, TopicSerializer

User = get_user_model()
username_field = User.USERNAME_FIELD


class UserView(RetrieveAPIView):

    queryset = User.objects.all()
    serializer_class = ProfileSerializer

    def get_object(self):
        queryset = self.get_queryset()
        user = get_object_or_404(queryset, **{username_field: self.kwargs['username']})
        return util.get_pybb_profile(user)


class UserPosts(PermissionsMixin, ListAPIView):

    pagination_class = PybbPostPagination
    queryset = Post.objects.all()
    serializer_class = PostSerializer

    def get_queryset(self):
        qs = super(UserPosts, self).get_queryset()
        user = get_object_or_404(User.objects.all(), **{username_field: self.kwargs['username']})
        qs = qs.filter(user=user)
        qs = self.perms.filter_posts(self.request.user, qs)
        qs = qs.order_by('-created', '-updated', '-id')
        return qs


class UserTopics(PermissionsMixin, ListAPIView):
    pagination_class = PybbTopicPagination
    queryset = Topic.objects.all()
    serializer_class = TopicSerializer

    def get_queryset(self):
        qs = super(UserTopics, self).get_queryset()
        user = get_object_or_404(User.objects.all(), **{username_field: self.kwargs['username']})
        qs = qs.filter(user=user)
        qs = self.perms.filter_topics(self.request.user, qs)
        qs = qs.order_by('-posts__updated', '-created', '-id')
        return qs


class ProfileEditView(UpdateAPIView):

    serializer_class = ProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return util.get_pybb_profile(self.request.user)
