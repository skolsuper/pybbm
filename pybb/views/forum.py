# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import F, Count
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views import generic
from django.views.decorators.csrf import csrf_protect

from pybb import settings as defaults, util
from pybb.models import Category, Forum, Topic, TopicReadTracker, ForumReadTracker
from pybb.templatetags.pybb_tags import pybb_topic_poll_not_voted
from pybb.views.mixins import RedirectToLoginMixin, PaginatorMixin, PybbFormsMixin
from pybb.permissions import PermissionsMixin


class IndexView(PermissionsMixin, generic.ListView):

    template_name = 'pybb/index.html'
    context_object_name = 'categories'

    def get_context_data(self, **kwargs):
        ctx = super(IndexView, self).get_context_data(**kwargs)
        categories = ctx['categories']
        for category in categories:
            category.forums_accessed = self.perms.filter_forums(self.request.user, category.forums.filter(parent=None))
        ctx['categories'] = categories
        return ctx

    def get_queryset(self):
        return self.perms.filter_categories(self.request.user, Category.objects.all())


class CategoryView(PermissionsMixin, RedirectToLoginMixin, generic.DetailView):

    template_name = 'pybb/index.html'
    context_object_name = 'category'

    def get_login_redirect_url(self):
        # returns super.get_object as there is a conflict with the self.perms.in CategoryView.get_object
        # Would raise a PermissionDenied and never redirect
        return super(CategoryView, self).get_object().get_absolute_url()

    def get_queryset(self):
        return Category.objects.all()

    def get_object(self, queryset=None):
        obj = super(CategoryView, self).get_object(queryset)
        if not self.perms.may_view_category(self.request.user, obj):
            raise PermissionDenied
        return obj

    def get_context_data(self, **kwargs):
        ctx = super(CategoryView, self).get_context_data(**kwargs)
        ctx['category'].forums_accessed = self.perms.filter_forums(self.request.user, ctx['category'].forums.filter(parent=None))
        ctx['categories'] = [ctx['category']]
        return ctx

    def get(self, *args, **kwargs):
        if defaults.settings.PYBB_NICE_URL and (('id' in kwargs) or ('pk' in kwargs)):
            return redirect(super(CategoryView, self).get_object(), permanent=defaults.settings.PYBB_NICE_URL_PERMANENT_REDIRECT)
        return super(CategoryView, self).get(*args, **kwargs)


class ForumView(PermissionsMixin, RedirectToLoginMixin, PaginatorMixin, generic.ListView):

    paginate_by = defaults.settings.PYBB_FORUM_PAGE_SIZE
    context_object_name = 'topic_list'
    template_name = 'pybb/forum.html'

    def dispatch(self, request, *args, **kwargs):
        self.forum = self.get_forum(**kwargs)
        return super(ForumView, self).dispatch(request, *args, **kwargs)

    def get_login_redirect_url(self):
        return self.forum.get_absolute_url()

    def get_context_data(self, **kwargs):
        ctx = super(ForumView, self).get_context_data(**kwargs)
        ctx['forum'] = self.forum
        ctx['forum'].forums_accessed = self.perms.filter_forums(self.request.user, self.forum.child_forums.all())
        return ctx

    def get_queryset(self):
        if not self.perms.may_view_forum(self.request.user, self.forum):
            raise PermissionDenied

        qs = self.forum.topics.order_by('-sticky', '-updated', '-id').select_related()
        qs = self.perms.filter_topics(self.request.user, qs)
        return qs

    def get_forum(self, **kwargs):
        if 'pk' in kwargs:
            forum = get_object_or_404(Forum.objects.all(), pk=kwargs['pk'])
        elif ('slug' and 'category_slug') in kwargs:
            forum = get_object_or_404(Forum, slug=kwargs['slug'], category__slug=kwargs['category_slug'])
        else:
            raise Http404(_('Forum does not exist'))
        return forum

    def get(self, *args, **kwargs):
        if defaults.settings.PYBB_NICE_URL and 'pk' in kwargs:
            return redirect(self.forum, permanent=defaults.settings.PYBB_NICE_URL_PERMANENT_REDIRECT)
        return super(ForumView, self).get(*args, **kwargs)


class LatestTopicsView(PermissionsMixin, PaginatorMixin, generic.ListView):

    paginate_by = defaults.settings.PYBB_FORUM_PAGE_SIZE
    context_object_name = 'topic_list'
    template_name = 'pybb/latest_topics.html'

    def get_queryset(self):
        qs = Topic.objects.all().select_related()
        qs = self.perms.filter_topics(self.request.user, qs)
        return qs.order_by('-updated', '-id')


class TopicView(PermissionsMixin, RedirectToLoginMixin, PaginatorMixin, PybbFormsMixin, generic.ListView):
    paginate_by = defaults.settings.PYBB_TOPIC_PAGE_SIZE
    template_object_name = 'post_list'
    template_name = 'pybb/topic.html'

    def get(self, request, *args, **kwargs):
        if defaults.settings.PYBB_NICE_URL and 'pk' in kwargs:
            return redirect(self.topic, permanent=defaults.settings.PYBB_NICE_URL_PERMANENT_REDIRECT)
        response = super(TopicView, self).get(request, *args, **kwargs)
        if self.request.user.is_authenticated():
            self.mark_read()
        return response

    def get_login_redirect_url(self):
        return self.topic.get_absolute_url()

    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        self.topic = self.get_topic(**kwargs)

        if request.GET.get('first-unread'):
            if request.user.is_authenticated():
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
        if not self.perms.may_view_topic(self.request.user, self.topic):
            raise PermissionDenied
        if self.request.user.is_authenticated() or not defaults.settings.PYBB_ANONYMOUS_VIEWS_CACHE_BUFFER:
            Topic.objects.filter(id=self.topic.id).update(views=F('views') + 1)
        else:
            cache_key = util.build_cache_key('anonymous_topic_views', topic_id=self.topic.id)
            cache.add(cache_key, 0)
            if cache.incr(cache_key) % defaults.settings.PYBB_ANONYMOUS_VIEWS_CACHE_BUFFER == 0:
                Topic.objects.filter(id=self.topic.id).update(views=F('views') +
                                                                defaults.settings.PYBB_ANONYMOUS_VIEWS_CACHE_BUFFER)
                cache.set(cache_key, 0)
        qs = self.topic.posts.all().select_related('user')
        if defaults.settings.PYBB_PROFILE_RELATED_NAME:
            qs = qs.select_related('user__%s' % defaults.settings.PYBB_PROFILE_RELATED_NAME)
        if not self.perms.may_moderate_topic(self.request.user, self.topic):
            qs = self.perms.filter_posts(self.request.user, qs)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super(TopicView, self).get_context_data(**kwargs)

        if self.request.user.is_authenticated():
            self.request.user.is_moderator = self.perms.may_moderate_topic(self.request.user, self.topic)
            self.request.user.is_subscribed = self.request.user in self.topic.subscribers.all()
            ctx['form'] = self.get_post_form_class()(topic=self.topic)
        elif defaults.settings.PYBB_ENABLE_ANONYMOUS_POST:
            ctx['form'] = self.get_post_form_class()(topic=self.topic)
        else:
            ctx['form'] = None
            ctx['next'] = self.get_login_redirect_url()
        if self.perms.may_attach_files(self.request.user):
            aformset = self.get_attachment_formset_class()()
            ctx['aformset'] = aformset
        if defaults.settings.PYBB_FREEZE_FIRST_POST:
            ctx['first_post'] = self.topic.head
        else:
            ctx['first_post'] = None
        ctx['topic'] = self.topic

        if self.perms.may_vote_in_topic(self.request.user, self.topic) and \
                pybb_topic_poll_not_voted(self.topic, self.request.user):
            ctx['poll_form'] = self.get_poll_form_class()(self.topic)

        return ctx

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
            readed_trackers = TopicReadTracker.objects.filter(
                user=self.request.user, topic__forum=self.topic.forum, time_stamp__gte=F('topic__updated'))
            unread = self.topic.forum.topics.exclude(topicreadtracker__in=readed_trackers)
            if forum_mark is not None:
                unread = unread.filter(updated__gte=forum_mark.time_stamp)

            if not unread.exists():
                # Clear all topic marks for this forum, mark forum as read
                TopicReadTracker.objects.filter(user=self.request.user, topic__forum=self.topic.forum).delete()
                forum_mark, new = ForumReadTracker.objects.get_or_create_tracker(
                    forum=self.topic.forum, user=self.request.user)
                forum_mark.save()

    def get_topic(self, **kwargs):
        if 'pk' in kwargs:
            topic = get_object_or_404(Topic.objects.annotate(Count('posts')), pk=kwargs['pk'], posts__count__gt=0)
        elif ('slug'and 'forum_slug'and 'category_slug') in kwargs:
            topic = get_object_or_404(
                Topic.objects.annotate(Count('posts')),
                slug=kwargs['slug'],
                forum__slug=kwargs['forum_slug'],
                forum__category__slug=kwargs['category_slug'],
                posts__count__gt=0
                )
        else:
            raise Http404(_('This topic does not exists'))
        return topic
