# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.html import strip_tags
from django.utils.timezone import now as tznow
from django.utils.translation import ugettext_lazy as _

from pybb.compat import get_user_model_path
from pybb.models.topic import Topic
from pybb.util import _get_markup_formatter, unescape


class RenderableItem(models.Model):
    """
    Base class for models that has markup, body, body_text and body_html fields.
    """

    class Meta(object):
        abstract = True

    body = models.TextField(_('Message'))
    body_html = models.TextField(_('HTML version'))
    body_text = models.TextField(_('Text version'))

    def render(self):
        self.body_html = _get_markup_formatter()(self.body)
        # Remove tags which was generated with the markup processor
        text = strip_tags(self.body_html)
        # Unescape entities which was generated with the markup processor
        self.body_text = unescape(text)


@python_2_unicode_compatible
class Post(RenderableItem):

    class Meta(object):
        ordering = ['created']
        verbose_name = _('Post')
        verbose_name_plural = _('Posts')
        app_label = 'pybb'

    topic = models.ForeignKey(Topic, related_name='posts', verbose_name=_('Topic'))
    user = models.ForeignKey(get_user_model_path(), related_name='posts', verbose_name=_('User'))
    created = models.DateTimeField(_('Created'), blank=True, db_index=True, auto_now_add=True)
    updated = models.DateTimeField(_('Updated'), blank=True, null=True)
    user_ip = models.IPAddressField(_('User IP'), blank=True, default='0.0.0.0')
    on_moderation = models.BooleanField(_('On moderation'), default=False)

    def summary(self):
        limit = 50
        tail = len(self.body) > limit and '...' or ''
        return self.body[:limit] + tail

    def __str__(self):
        return self.summary()

    def save(self, *args, **kwargs):
        self.render()

        new = self.pk is None

        topic_changed = False
        old_post = None
        if not new:
            self.updated = tznow()
            old_post = Post.objects.get(pk=self.pk)
            if old_post.topic != self.topic:
                topic_changed = True

        super(Post, self).save(*args, **kwargs)

        # If post is topic head and moderated, moderate topic too
        if self.topic.head == self and not self.on_moderation and self.topic.on_moderation:
            self.topic.on_moderation = False

        updated = self.updated or self.created
        self.topic.updated = updated
        self.topic.save()
        self.topic.forum.updated = updated
        self.topic.forum.save()

        if topic_changed:
            old_post.topic.update_counters()
            old_post.topic.forum.update_counters()

    def get_absolute_url(self):
        return reverse('pybb:post', kwargs={'pk': self.id})

    def delete(self, *args, **kwargs):
        self_id = self.id
        head_post_id = self.topic.posts.order_by('created', 'id')[0].id

        if self_id == head_post_id:
            forum = self.topic.forum
            self.topic.delete()
            forum.update_counters()
        else:
            super(Post, self).delete(*args, **kwargs)
            self.topic.update_counters()
            self.topic.forum.update_counters()

    def get_parents(self):
        """
        Used in templates for breadcrumb building
        """
        return self.topic.forum.category, self.topic.forum, self.topic,
