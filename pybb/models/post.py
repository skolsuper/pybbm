# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from pybb.compat import get_user_model_path

from .renderable import RenderableItem


@python_2_unicode_compatible
class Post(RenderableItem):
    topic = models.ForeignKey('Topic', related_name='posts', verbose_name=_('Topic'))
    user = models.ForeignKey(get_user_model_path(), related_name='posts', verbose_name=_('User'))
    created = models.DateTimeField(_('Created'), blank=True, db_index=True, auto_now_add=True)
    updated = models.DateTimeField(_('Updated'), blank=True, null=True)
    user_ip = models.IPAddressField(_('User IP'), blank=True, default='0.0.0.0')
    on_moderation = models.BooleanField(_('On moderation'), default=False)

    class Meta(object):
        ordering = ['created']
        verbose_name = _('Post')
        verbose_name_plural = _('Posts')
        app_label = 'pybb'

    def summary(self):
        limit = 50
        tail = len(self.body) > limit and '...' or ''
        return self.body[:limit] + tail

    def __str__(self):
        return self.summary()

    def save(self, *args, **kwargs):
        self.render()

        topic_changed = False
        if self.pk is not None:
            old_post = Post.objects.get(pk=self.pk)
            topic_changed = old_post.topic != self.topic

        super(Post, self).save(*args, **kwargs)

        # If post is topic head and moderated, moderate topic too
        if self.topic.head == self and not self.on_moderation and self.topic.on_moderation:
            self.topic.on_moderation = False

        self.topic.update_counters()

        if topic_changed:
            old_post.topic.update_counters()

    def get_absolute_url(self):
        return reverse('pybb:post', kwargs={'pk': self.id})

    def delete(self, *args, **kwargs):
        topic = self.topic
        topic_head = self == topic.head
        super(Post, self).delete(*args, **kwargs)
        if topic_head:
            topic.delete()
        else:
            topic.update_counters()

    def get_parents(self):
        """
        Used in templates for breadcrumb building
        """
        return self.topic.forum.category, self.topic.forum, self.topic,
