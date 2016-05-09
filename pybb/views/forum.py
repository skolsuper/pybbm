# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.cache import cache
from django.db.models import F, Count, Max
from django.shortcuts import redirect, get_object_or_404
from django.utils.timezone import now
from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ParseError
from rest_framework.generics import RetrieveAPIView, ListAPIView, ListCreateAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from pybb import util
from pybb.models import Category, Forum, Topic
from pybb.pagination import PybbTopicPagination
from pybb.permissions import PermissionsMixin
from pybb.read_tracking import mark_read
from pybb.serializers import ForumSerializer, TopicSerializer, CategorySerializer
from pybb.settings import settings


class CategoryList(PermissionsMixin, ListAPIView):

    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_queryset(self):
        return self.perms.filter_categories(self.request.user, self.queryset)


class CategoryView(PermissionsMixin, RetrieveAPIView):

    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_queryset(self):
        return self.perms.filter_categories(self.request.user, self.queryset)

    def get_object(self):
        if 'pk' in self.kwargs:
            lookup = {'pk': self.kwargs['pk']}
        elif 'slug' in self.kwargs:
            lookup = {'slug': self.kwargs['slug']}
        else:
            raise NotFound
        obj = get_object_or_404(self.get_queryset(), **lookup)
        if not self.perms.may_view_category(self.request.user, obj):
            raise PermissionDenied
        return obj

    def get(self, *args, **kwargs):
        if settings.PYBB_NICE_URL and (('id' in kwargs) or ('pk' in kwargs)):
            return redirect(super(CategoryView, self).get_object(), permanent=settings.PYBB_NICE_URL_PERMANENT_REDIRECT)
        return super(CategoryView, self).get(*args, **kwargs)


class ForumList(PermissionsMixin, ListAPIView):

    queryset = Forum.objects.all()
    serializer_class = ForumSerializer
    pagination_class = PybbTopicPagination

    def get_queryset(self):
        return self.perms.filter_forums(self.request.user, self.queryset)


class ForumView(PermissionsMixin, RetrieveAPIView):

    queryset = Forum.objects.all()
    serializer_class = ForumSerializer

    def get_queryset(self):
        return self.perms.filter_forums(self.request.user, self.queryset)

    def get_object(self):
        if 'pk' in self.kwargs:
            lookup = {'pk': self.kwargs['pk']}
        elif ('slug' and 'category_slug') in self.kwargs:
            lookup = {'slug': self.kwargs['slug'], 'category__slug': self.kwargs['category_slug']}
        else:
            raise NotFound
        forum = get_object_or_404(self.get_queryset(), **lookup)
        if not self.perms.may_view_forum(self.request.user, forum):
            raise PermissionDenied
        return forum

    def get(self, request, *args, **kwargs):
        if settings.PYBB_NICE_URL and 'pk' in kwargs:
            return redirect(self.get_object().get_absolute_url(), permanent=settings.PYBB_NICE_URL_PERMANENT_REDIRECT)
        return super(ForumView, self).get(request, *args, **kwargs)


class ListCreateTopicsView(PermissionsMixin, ListCreateAPIView):

    pagination_class = PybbTopicPagination
    queryset = Topic.objects.annotate(post_count=Count('posts'), last_update=Max('posts__updated'))
    serializer_class = TopicSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = self.perms.filter_topics(self.request.user, self.queryset)
        forum_pk = self.request.query_params.get('forum', None)
        if forum_pk is not None:
            qs = qs.filter(forum__pk=forum_pk)
        return qs.order_by('sticky', '-last_update', '-id')

    def create(self, request, *args, **kwargs):
        try:
            forum = Forum.objects.get(pk=request.data['forum'])
        except Forum.DoesNotExist:
            raise ParseError(_('Specified forum not found.'))
        if not self.perms.may_create_topic(request.user, forum):
            self.permission_denied(request, _('You do not have permission to create topics in this forum.'))
        if 'poll_question' in request.data and not self.perms.may_create_poll(request.user):
            raise PermissionDenied(_('You do not have permission to create a poll.'))

        topic_data = request.data.copy()
        topic_data['user'] = request.user.id
        topic_data['on_moderation'] = not self.perms.may_create_topic_unmoderated(request.user, forum)
        serializer = self.get_serializer(data=topic_data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        mark_read(request.user, serializer.instance, now())
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class UpdateTopicView(PermissionsMixin, UpdateAPIView):

    queryset = Topic.objects.all()
    serializer_class = TopicSerializer

    def get_object(self):
        qs = self.get_queryset()
        topic = get_object_or_404(qs, pk=self.kwargs['pk'])
        if not self.perms.may_edit_post(self.request.user, topic.head):
            raise PermissionDenied
        return topic

    def update(self, request, *args, **kwargs):
        data = request.data.copy()
        instance = self.get_object()
        data['user'] = instance.user.pk
        serializer = self.get_serializer(instance, data=data)
        serializer.is_valid(raise_exception=True)
        instance.poll_answers.all().delete()  # partial updates not allowed, this is easiest
        instance.poll_question = ''
        instance.save()
        self.perform_update(serializer)
        return Response(serializer.data)


class TopicView(PermissionsMixin, RetrieveAPIView):
    queryset = Topic.objects.annotate(Count('posts'))
    serializer_class = TopicSerializer

    def get(self, request, *args, **kwargs):
        if settings.PYBB_NICE_URL and 'pk' in kwargs:
            return redirect(self.get_object(), permanent=settings.PYBB_NICE_URL_PERMANENT_REDIRECT)
        response = super(TopicView, self).get(request, *args, **kwargs)
        self.bump_view_count()
        return response

    def get_queryset(self):
        return self.perms.filter_topics(self.request.user, self.queryset)

    def get_object(self):
        if 'pk' in self.kwargs:
            lookup = {'pk': self.kwargs['pk']}
        elif ('slug'and 'forum_slug'and 'category_slug') in self.kwargs:
            lookup = {
                'slug': self.kwargs['slug'],
                'forum__slug': self.kwargs['forum_slug'],
                'forum__category__slug': self.kwargs['category_slug']
            }
        else:
            raise NotFound
        self.topic = get_object_or_404(self.get_queryset(), **lookup)
        return self.topic

    def bump_view_count(self):
        topic_qs = Topic.objects.filter(id=self.get_object().id)
        cache_buffer = settings.PYBB_ANONYMOUS_VIEWS_CACHE_BUFFER
        if self.request.user.is_authenticated() or not cache_buffer:
            topic_qs.update(views=F('views') + 1)
        else:
            cache_key = util.build_cache_key('anonymous_topic_views', topic_id=self.topic.id)
            cache.add(cache_key, 0)
            if cache.incr(cache_key) % cache_buffer == 0:
                topic_qs.update(views=F('views') + cache_buffer)
                cache.set(cache_key, 0)
