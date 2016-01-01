# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings as django_settings
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Max
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from pybb.models.post import Post
from pybb.models.topic import Topic
from pybb.settings import settings


@python_2_unicode_compatible
class Forum(models.Model):

    class Meta(object):
        ordering = ['position']
        verbose_name = _('Forum')
        verbose_name_plural = _('Forums')
        unique_together = ('category', 'slug')
        app_label = 'pybb'

    category = models.ForeignKey('Category', related_name='forums', verbose_name=_('Category'))
    parent = models.ForeignKey('self', related_name='child_forums', verbose_name=_('Parent forum'),
                               blank=True, null=True)
    name = models.CharField(_('Name'), max_length=80)
    position = models.IntegerField(_('Position'), blank=True, default=0)
    description = models.TextField(_('Description'), blank=True)
    moderators = models.ManyToManyField(django_settings.AUTH_USER_MODEL, blank=True, null=True, verbose_name=_('Moderators'))
    hidden = models.BooleanField(_('Hidden'), blank=False, null=False, default=False)
    readed_by = models.ManyToManyField(django_settings.AUTH_USER_MODEL, through='ForumReadTracker', related_name='readed_forums')
    headline = models.TextField(_('Headline'), blank=True, null=True)

    slug = models.SlugField(verbose_name=_("Slug"), max_length=255)

    def __str__(self):
        return self.name

    @property
    def updated(self):
        try:
            return self.posts.order_by('-updated')[0].updated
        except IndexError:
            return None

    @cached_property
    def topics(self):
        return Topic.objects.filter(forum=self)\
                            .annotate(last_update=Max('posts__updated'))\
                            .order_by('-sticky', '-last_update', '-id')

    def get_absolute_url(self):
        if settings.PYBB_NICE_URL:
            return reverse('pybb:forum', kwargs={'slug': self.slug, 'category_slug': self.category.slug})
        return reverse('pybb:forum', kwargs={'pk': self.id})

    @property
    def posts(self):
        return Post.objects.filter(topic__forum=self)

    @cached_property
    def last_post(self):
        try:
            return self.posts.order_by('-created', '-id')[0]
        except IndexError:
            return None

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
