# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.exceptions import PermissionDenied, ValidationError
from django.forms.utils import ErrorList
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.utils.decorators import method_decorator

from pybb import defaults, compat
from pybb.compat import get_atomic_func
from pybb.forms import PostForm, AttachmentFormSet, PollForm, PollAnswerFormSet
from pybb.models import Topic, Post
from pybb.permissions import perms
from pybb.signals import topic_updated

Paginator, pure_pagination = compat.get_paginator_class()


class PaginatorMixin(object):
    def get_paginator(self, queryset, per_page, orphans=0, allow_empty_first_page=True, **kwargs):
        kwargs = {}
        if pure_pagination:
            kwargs['request'] = self.request
        return Paginator(queryset, per_page, orphans, allow_empty_first_page, **kwargs)


class RedirectToLoginMixin(object):
    """ mixin which redirects to settings.LOGIN_URL if the view encounters an PermissionDenied exception
        and the user is not authenticated. Views inheriting from this need to implement
        get_login_redirect_url(), which returns the URL to redirect to after login (parameter "next")
    """
    def dispatch(self, request, *args, **kwargs):
        try:
            return super(RedirectToLoginMixin, self).dispatch(request, *args, **kwargs)
        except PermissionDenied:
            if not request.user.is_authenticated():
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(self.get_login_redirect_url())
            else:
                return HttpResponseForbidden()

    def get_login_redirect_url(self):
        """ get the url to which we redirect after the user logs in. subclasses should override this """
        return '/'


class PybbFormsMixin(object):

    post_form_class = PostForm
    attachment_formset_class = AttachmentFormSet
    poll_form_class = PollForm
    poll_answer_formset_class = PollAnswerFormSet

    def get_post_form_class(self):
        return self.post_form_class

    def get_attachment_formset_class(self):
        return self.attachment_formset_class

    def get_poll_form_class(self):
        return self.poll_form_class

    def get_poll_answer_formset_class(self):
        return self.poll_answer_formset_class


class PostEditMixin(PybbFormsMixin):

    @method_decorator(get_atomic_func())
    def post(self, request, *args, **kwargs):
        return super(PostEditMixin, self).post(request, *args, **kwargs)

    def get_form_class(self):
        return self.get_post_form_class()

    def get_context_data(self, **kwargs):

        ctx = super(PostEditMixin, self).get_context_data(**kwargs)

        if perms.may_attach_files(self.request.user) and 'aformset' not in kwargs:
            ctx['aformset'] = self.get_attachment_formset_class()(
                instance=getattr(self, 'object', None)
            )

        if perms.may_create_poll(self.request.user) and 'pollformset' not in kwargs:
            ctx['pollformset'] = self.get_poll_answer_formset_class()(
                instance=self.object.topic if getattr(self, 'object', None) else None
            )

        return ctx

    def form_valid(self, form):
        success = True
        save_attachments = False
        save_poll_answers = False
        self.object, topic = form.save(commit=False)

        if perms.may_attach_files(self.request.user):
            aformset = self.get_attachment_formset_class()(
                self.request.POST, self.request.FILES, instance=self.object
            )
            if aformset.is_valid():
                save_attachments = True
            else:
                success = False
        else:
            aformset = None

        if perms.may_create_poll(self.request.user):
            pollformset = self.get_poll_answer_formset_class()()
            if getattr(self, 'forum', None) or topic.head == self.object:
                if topic.poll_type != Topic.POLL_TYPE_NONE:
                    pollformset = self.get_poll_answer_formset_class()(
                        self.request.POST, instance=topic
                    )
                    if pollformset.is_valid():
                        save_poll_answers = True
                    else:
                        success = False
                else:
                    topic.poll_question = None
                    topic.poll_answers.all().delete()
        else:
            pollformset = None

        if success:
            try:
                topic.save()
            except ValidationError as e:
                success = False
                errors = form._errors.setdefault('name', ErrorList())
                errors += e.error_list
            else:
                self.object.topic = topic

                created = self.object.id is None
                self.object.save()

                if created or defaults.PYBB_NOTIFY_ON_EDIT:
                    topic_updated.send(Post, post=self.object, current_site=compat.get_current_site(self.request))
                if save_attachments:
                    aformset.save()
                if save_poll_answers:
                    pollformset.save()
                return HttpResponseRedirect(self.get_success_url())
        return self.render_to_response(self.get_context_data(form=form,
                                                             aformset=aformset,
                                                             pollformset=pollformset))
