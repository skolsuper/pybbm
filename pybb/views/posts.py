# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import math

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.csrf import csrf_protect

from pybb import compat, settings as defaults, util
from pybb.models import Forum, Topic, Post
from pybb.views.mixins import PostEditMixin, RedirectToLoginMixin
from pybb.permissions import PermissionsMixin

User = get_user_model()
username_field = compat.get_username_field()


class AddPostView(PostEditMixin, generic.CreateView):

    template_name = 'pybb/add_post.html'

    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            self.user = request.user
        else:
            if defaults.settings.PYBB_ENABLE_ANONYMOUS_POST:
                self.user, new = User.objects.get_or_create(**{username_field: defaults.settings.PYBB_ANONYMOUS_USERNAME})
            else:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())

        self.forum = None
        self.topic = None
        if 'forum_id' in kwargs:
            self.forum = get_object_or_404(self.perms.filter_forums(request.user, Forum.objects.all()), pk=kwargs['forum_id'])
            if not self.perms.may_create_topic(self.user, self.forum):
                raise PermissionDenied
        elif 'topic_id' in kwargs:
            self.topic = get_object_or_404(self.perms.filter_topics(request.user, Topic.objects.all()), pk=kwargs['topic_id'])
            if not self.perms.may_create_post(self.user, self.topic):
                raise PermissionDenied

            self.quote = ''
            if 'quote_id' in request.GET:
                try:
                    quote_id = int(request.GET.get('quote_id'))
                except TypeError:
                    raise Http404
                else:
                    post = get_object_or_404(Post, pk=quote_id)
                    if not self.perms.may_view_post(request.user, post):
                        raise PermissionDenied
                    profile = util.get_pybb_profile(post.user)
                    self.quote = util._get_markup_quoter(defaults.settings.PYBB_MARKUP)(post.body, profile.get_display_name())

                if self.quote and request.is_ajax():
                    return HttpResponse(self.quote)
        return super(AddPostView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        ip = self.request.META.get('REMOTE_ADDR', '')
        form_kwargs = super(AddPostView, self).get_form_kwargs()
        form_kwargs.update(dict(topic=self.topic, forum=self.forum, user=self.user,
                           ip=ip, initial={}))
        if getattr(self, 'quote', None):
            form_kwargs['initial']['body'] = self.quote
        form_kwargs['may_create_poll'] = self.perms.may_create_poll(self.user)
        form_kwargs['may_edit_topic_slug'] = self.perms.may_edit_topic_slug(self.user)
        return form_kwargs

    def get_context_data(self, **kwargs):
        ctx = super(AddPostView, self).get_context_data(**kwargs)
        ctx['forum'] = self.forum
        ctx['topic'] = self.topic
        return ctx

    def get_success_url(self):
        if (not self.request.user.is_authenticated()) and defaults.settings.PYBB_PREMODERATION:
            return reverse('pybb:index')
        return self.object.get_absolute_url()


class EditPostView(PostEditMixin, generic.UpdateView):

    model = Post

    context_object_name = 'post'
    template_name = 'pybb/edit_post.html'

    @method_decorator(login_required)
    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        return super(EditPostView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        form_kwargs = super(EditPostView, self).get_form_kwargs()
        form_kwargs['may_create_poll'] = self.perms.may_create_poll(self.request.user)
        return form_kwargs

    def get_object(self, queryset=None):
        post = super(EditPostView, self).get_object(queryset)
        if not self.perms.may_edit_post(self.request.user, post):
            raise PermissionDenied
        return post


class PostView(PermissionsMixin, RedirectToLoginMixin, generic.RedirectView):

    permanent = False

    def dispatch(self, request, *args, **kwargs):
        self.post = self.get_post(**kwargs)
        return super(PostView, self).dispatch(request, *args, **kwargs)

    def get_login_redirect_url(self):
        return self.post.get_absolute_url()

    def get_redirect_url(self, **kwargs):
        if not self.perms.may_view_post(self.request.user, self.post):
            raise PermissionDenied
        count = self.post.topic.posts.filter(created__lt=self.post.created).count() + 1
        page = math.ceil(count / float(defaults.settings.PYBB_TOPIC_PAGE_SIZE))
        return '%s?page=%d#post-%d' % (self.post.topic.get_absolute_url(), page, self.post.id)

    def get_post(self, **kwargs):
        return get_object_or_404(Post, pk=kwargs['pk'])


class ModeratePost(PermissionsMixin, generic.RedirectView):

    permanent = False

    def get_redirect_url(self, **kwargs):
        post = get_object_or_404(Post, pk=self.kwargs['pk'])
        if not self.perms.may_moderate_topic(self.request.user, post.topic):
            raise PermissionDenied
        post.on_moderation = False
        post.save()
        return post.get_absolute_url()


class DeletePostView(PermissionsMixin, generic.DeleteView):

    template_name = 'pybb/delete_post.html'
    context_object_name = 'post'

    def get_object(self, queryset=None):
        post = get_object_or_404(Post.objects.select_related('topic', 'topic__forum'), pk=self.kwargs['pk'])
        if not self.perms.may_delete_post(self.request.user, post):
            raise PermissionDenied
        self.topic = post.topic
        self.forum = post.topic.forum
        if not self.perms.may_moderate_topic(self.request.user, self.topic):
            raise PermissionDenied
        return post

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        redirect_url = self.get_success_url()
        if not request.is_ajax():
            return HttpResponseRedirect(redirect_url)
        else:
            return HttpResponse(redirect_url)

    def get_success_url(self):
        try:
            Topic.objects.get(pk=self.topic.id)
        except Topic.DoesNotExist:
            return self.forum.get_absolute_url()
        else:
            if not self.request.is_ajax():
                return self.topic.get_absolute_url()
            else:
                return ""
