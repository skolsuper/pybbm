# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import F, Count, Max
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, get_object_or_404
from rest_framework.exceptions import NotFound
from rest_framework.generics import RetrieveAPIView, ListAPIView

from pybb import util
from pybb.models import Category, Forum, Topic, TopicReadTracker, ForumReadTracker
from pybb.permissions import PermissionsMixin
from pybb.serializers import ForumSerializer, TopicSerializer, CategorySerializer
from pybb.settings import settings
from pybb.views.mixins import PaginatorMixin


class CategoryList(PermissionsMixin, ListAPIView):

    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_queryset(self):
        return self.perms.filter_categories(self.request.user, self.queryset)


class CategoryView(PermissionsMixin, RetrieveAPIView):

    queryset = Category.objects.all()
    serializer_class = CategorySerializer

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


class LatestTopicsView(PermissionsMixin, PaginatorMixin, ListAPIView):

    paginate_by = settings.PYBB_FORUM_PAGE_SIZE
    queryset = Topic.objects.annotate(Count('posts'), last_update=Max('posts__updated'))
    serializer_class = TopicSerializer

    def get_queryset(self):
        qs = self.perms.filter_topics(self.request.user, self.queryset)
        return qs.order_by('-last_update', '-id')


class TopicView(PermissionsMixin, PaginatorMixin, RetrieveAPIView):
    queryset = Topic.objects.annotate(Count('posts'))
    serializer_class = TopicSerializer

    def get(self, request, *args, **kwargs):
        if settings.PYBB_NICE_URL and 'pk' in kwargs:
            return redirect(self.topic, permanent=settings.PYBB_NICE_URL_PERMANENT_REDIRECT)
        response = super(TopicView, self).get(request, *args, **kwargs)
        self.bump_view_count()
        if self.request.user.is_authenticated():
            self.mark_read()
        return response

    def dispatch(self, request, *args, **kwargs):
        self.topic = self.get_object()

        if request.GET.get('first-unread') and request.user.is_authenticated():
            read_dates = []
            try:
                read_dates.append(TopicReadTracker.objects.get(user=request.user, topic=self.topic).time_stamp)
            except TopicReadTracker.DoesNotExist:
                pass
            try:
                read_dates.append(ForumReadTracker.objects.get(user=request.user, forum=self.topic.forum).time_stamp)
            except ForumReadTracker.DoesNotExist:
                pass

            read_date = read_dates and max(read_dates)
            if read_date:
                try:
                    first_unread_topic = self.topic.posts.filter(created__gt=read_date).order_by('created', 'id')[0]
                except IndexError:
                    first_unread_topic = self.topic.last_post
            else:
                first_unread_topic = self.topic.head
            return HttpResponseRedirect(reverse('pybb:post', kwargs={'pk': first_unread_topic.id}))

        return super(TopicView, self).dispatch(request, *args, **kwargs)

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
        topic = get_object_or_404(self.get_queryset(), **lookup)
        return topic

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

    def mark_read(self):
        try:
            forum_mark = ForumReadTracker.objects.get(forum=self.topic.forum, user=self.request.user)
        except ForumReadTracker.DoesNotExist:
            forum_mark = None
        if (forum_mark is None) or (forum_mark.time_stamp < self.topic.updated):
            topic_mark, new = TopicReadTracker.objects.get_or_create_tracker(topic=self.topic, user=self.request.user)
            if not new and topic_mark.time_stamp > self.topic.updated:
                # Bail early if we already read this thread.
                return

            # Check, if there are any unread topics in forum
            readed_trackers = TopicReadTracker.objects\
                .annotate(last_update=Max('topic__posts__updated'))\
                .filter(user=self.request.user, topic__forum=self.topic.forum, time_stamp__gte=F('last_update'))
            unread = self.topic.forum.topics.exclude(topicreadtracker__in=readed_trackers)
            if forum_mark is not None:
                unread = unread.annotate(
                    last_update=Max('posts__updated')).filter(last_update__gte=forum_mark.time_stamp)

            if not unread.exists():
                # Clear all topic marks for this forum, mark forum as read
                TopicReadTracker.objects.filter(user=self.request.user, topic__forum=self.topic.forum).delete()
                forum_mark, new = ForumReadTracker.objects.get_or_create_tracker(
                    forum=self.topic.forum, user=self.request.user)
                forum_mark.save()
