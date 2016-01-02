# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.generics import RetrieveAPIView, ListAPIView, UpdateAPIView

from pybb import settings as defaults, util
from pybb.models import Topic, Post
from pybb.permissions import PermissionsMixin
from pybb.serializers import ProfileSerializer, PostSerializer, TopicSerializer
from pybb.views.mixins import PaginatorMixin

User = get_user_model()
username_field = User.USERNAME_FIELD

Profile = util.get_pybb_profile_model()


class UserView(RetrieveAPIView):

    queryset = User.objects.all()
    serializer_class = ProfileSerializer

    def get_object(self):
        queryset = self.get_queryset()
        user = get_object_or_404(queryset, **{username_field: self.kwargs['username']})
        return util.get_pybb_profile(user)


class UserPosts(PermissionsMixin, PaginatorMixin, ListAPIView):

    paginate_by = defaults.settings.PYBB_TOPIC_PAGE_SIZE
    queryset = Post.objects.all()
    serializer_class = PostSerializer

    def get_queryset(self):
        qs = super(UserPosts, self).get_queryset()
        user = get_object_or_404(User.objects.all(), **{username_field: self.kwargs['username']})
        qs = qs.filter(user=user)
        qs = self.perms.filter_posts(self.request.user, qs)
        qs = qs.order_by('-created', '-updated', '-id')
        return qs


class UserTopics(PermissionsMixin, PaginatorMixin, ListAPIView):
    paginate_by = defaults.settings.PYBB_FORUM_PAGE_SIZE
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

    def get_object(self):
        return util.get_pybb_profile(self.request.user)
