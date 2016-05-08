# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now as tznow
from django.utils.translation import ugettext_lazy as _

from pybb.models.topic import Topic
from pybb.settings import settings as pybb_settings
from pybb.util import FilePathGenerator


@python_2_unicode_compatible
class Post(models.Model):

    class Meta(object):
        ordering = ['created']
        verbose_name = _('Post')
        verbose_name_plural = _('Posts')

    body = models.TextField(_('Message'))
    topic = models.ForeignKey(Topic, related_name='posts', verbose_name=_('Topic'))
    user = models.ForeignKey(
            settings.AUTH_USER_MODEL, null=True, related_name='posts', verbose_name=_('User'))
    created = models.DateTimeField(_('Created'), blank=True, db_index=True, auto_now_add=True)
    updated = models.DateTimeField(_('Updated'), blank=True, db_index=True, auto_now=True)
    user_ip = models.GenericIPAddressField(_('User IP'))
    on_moderation = models.BooleanField(_('On moderation'), default=False)
    attachment = models.FileField(_('Attachment'), blank=True, upload_to=FilePathGenerator(to=pybb_settings.PYBB_ATTACHMENT_UPLOAD_TO))

    def summary(self):
        limit = 50
        tail = len(self.body) > limit and '...' or ''
        return self.body[:limit] + tail

    def __str__(self):
        return self.summary()

    def save(self, *args, **kwargs):
        super(Post, self).save(*args, **kwargs)

        # If post is topic head and moderated, moderate topic too
        if self.topic.head == self and not self.on_moderation and self.topic.on_moderation:
            self.topic.on_moderation = False
            self.topic.save()

    def get_absolute_url(self):
        return reverse('pybb:post', kwargs={'pk': self.id})

    def delete(self, *args, **kwargs):
        self_id = self.id
        head_post_id = self.topic.posts.order_by('created', 'id')[0].id

        if self_id == head_post_id:
            self.topic.delete()
        else:
            super(Post, self).delete(*args, **kwargs)

    def get_parents(self):
        """
        Used in templates for breadcrumb building
        """
        return self.topic.forum.category, self.topic.forum, self.topic,
