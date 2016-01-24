# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _


class TopicReadTracker(models.Model):
    """
    Save per user topic read tracking
    """

    class Meta(object):
        verbose_name = _('Topic read tracker')
        verbose_name_plural = _('Topic read trackers')
        unique_together = ('user', 'topic')

    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    topic = models.ForeignKey('Topic')
    time_stamp = models.DateTimeField()


class ForumReadTracker(models.Model):
    """
    Save per user forum read tracking
    """

    class Meta(object):
        verbose_name = _('Forum read tracker')
        verbose_name_plural = _('Forum read trackers')
        unique_together = ('user', 'forum')

    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    forum = models.ForeignKey('Forum')
    time_stamp = models.DateTimeField()
