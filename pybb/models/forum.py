# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import VERSION as DJANGO_VERSION
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from pybb.compat import get_user_model_path

from .post import Post

@python_2_unicode_compatible
class Forum(models.Model):
    category = models.ForeignKey('Category', related_name='forums', verbose_name=_('Category'))
    parent = models.ForeignKey('self', related_name='child_forums', verbose_name=_('Parent forum'),
                               blank=True, null=True)
    name = models.CharField(_('Name'), max_length=80)
    position = models.IntegerField(_('Position'), blank=True, default=0)
    description = models.TextField(_('Description'), blank=True)
    moderators = models.ManyToManyField(get_user_model_path(), blank=True, null=True, verbose_name=_('Moderators'))
    hidden = models.BooleanField(_('Hidden'), blank=False, null=False, default=False)
    readed_by = models.ManyToManyField(get_user_model_path(), through='ForumReadTracker', related_name='readed_forums')
    headline = models.TextField(_('Headline'), blank=True, null=True)

    class Meta(object):
        ordering = ['position']
        verbose_name = _('Forum')
        verbose_name_plural = _('Forums')
        app_label = 'pybb'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('pybb:forum', kwargs={'pk': self.id})

    @cached_property
    def topic_count(self):
        return self.topics.count()

    @property
    def post_count(self):
        return self.posts.count()

    @property
    def updated(self):
        if self.last_post is not None:
            return self.last_post.created
        return None

    @cached_property
    def posts(self):
        return Post.objects.filter(topic__forum=self)

    if DJANGO_VERSION >= (1,7):
        @cached_property
        def last_post(self):
            #default ordering on Post model is by 'created'
            return self.posts.last()

    else:
        @cached_property
        def last_post(self):
            return self.posts.all()[self.post_count - 1]

    def get_parents(self):
        """
        Used in templates for breadcrumb building
        """
        parents = [self.category]
        parent = self.parent
        while parent is not None:
            parents.insert(1, parent)
            parent = parent.parent
        return parents
