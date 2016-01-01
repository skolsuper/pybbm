# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings as django_settings
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from pybb.models.poll import PollAnswerUser
from pybb.settings import settings


@python_2_unicode_compatible
class Topic(models.Model):

    class Meta(object):
        ordering = ['-created']
        verbose_name = _('Topic')
        verbose_name_plural = _('Topics')
        unique_together = ('forum', 'slug')
        app_label = 'pybb'

    POLL_TYPE_NONE = 0
    POLL_TYPE_SINGLE = 1
    POLL_TYPE_MULTIPLE = 2

    POLL_TYPE_CHOICES = (
        (POLL_TYPE_NONE, _('None')),
        (POLL_TYPE_SINGLE, _('Single answer')),
        (POLL_TYPE_MULTIPLE, _('Multiple answers')),
    )

    forum = models.ForeignKey('Forum', related_name='topics', verbose_name=_('Forum'))
    name = models.CharField(_('Subject'), max_length=255)
    created = models.DateTimeField(_('Created'), auto_now_add=True)
    user = models.ForeignKey(django_settings.AUTH_USER_MODEL, related_name='topics', verbose_name=_('User'))
    views = models.IntegerField(_('Views count'), blank=True, default=0)
    sticky = models.BooleanField(_('Sticky'), blank=True, default=False)
    closed = models.BooleanField(_('Closed'), blank=True, default=False)
    subscribers = models.ManyToManyField(django_settings.AUTH_USER_MODEL, related_name='subscriptions',
                                         verbose_name=_('Subscribers'), blank=True)
    readed_by = models.ManyToManyField(django_settings.AUTH_USER_MODEL, through='TopicReadTracker', related_name='readed_topics')
    on_moderation = models.BooleanField(_('On moderation'), default=False)
    poll_type = models.IntegerField(_('Poll type'), choices=POLL_TYPE_CHOICES, default=POLL_TYPE_NONE)
    poll_question = models.TextField(_('Poll question'), blank=True, null=True)

    slug = models.SlugField(verbose_name=_("Slug"), max_length=255)

    def __str__(self):
        return self.name

    @property
    def updated(self):
        try:
            return self.posts.order_by('updated').reverse()[0].updated
        except IndexError:
            return None

    @cached_property
    def head(self):
        try:
            return self.posts.all().order_by('created', 'id')[0]
        except IndexError:
            return None

    @cached_property
    def last_post(self):
        try:
            return self.posts.order_by('-created', '-id').select_related('user')[0]
        except IndexError:
            return None

    def get_absolute_url(self):
        if settings.PYBB_NICE_URL:
            return reverse('pybb:topic', kwargs={'slug': self.slug, 'forum_slug': self.forum.slug, 'category_slug': self.forum.category.slug})
        return reverse('pybb:topic', kwargs={'pk': self.id})

    def get_parents(self):
        """
        Used in templates for breadcrumb building
        """
        parents = self.forum.get_parents()
        parents.append(self.forum)
        return parents

    def poll_votes(self):
        if self.poll_type != self.POLL_TYPE_NONE:
            return PollAnswerUser.objects.filter(poll_answer__topic=self).count()
        else:
            return None
