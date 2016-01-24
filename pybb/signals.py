# coding=utf-8
from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_save
from django.dispatch import Signal, receiver

from pybb import util
from pybb.models import Post, Category, Topic, Forum
from pybb.permissions import get_perms
from pybb.settings import settings
from pybb.util import create_or_check_slug

topic_updated = Signal(providing_args=['post', 'request'])


@receiver(post_save, sender=Post)
def forum_post_saved(sender, instance, created, **kwargs):
    if created and \
            instance.user is not None and \
            not settings.PYBB_DISABLE_SUBSCRIPTIONS and \
            util.get_pybb_profile(instance.user).autosubscribe and \
            get_perms().may_subscribe_topic(instance.user, instance.topic):
        instance.topic.subscribers.add(instance.user)


def user_saved(sender, instance, created, **kwargs):
    if not created:
        return

    try:
        add_post_permission = Permission.objects.get_by_natural_key('add_post', 'pybb', 'post')
        add_topic_permission = Permission.objects.get_by_natural_key('add_topic', 'pybb', 'topic')
    except (Permission.DoesNotExist, ContentType.DoesNotExist):
        return
    instance.user_permissions.add(add_post_permission, add_topic_permission)

    if settings.PYBB_PROFILE_RELATED_NAME:
        ModelProfile = util.get_pybb_profile_model()
        profile = ModelProfile()
        setattr(instance, settings.PYBB_PROFILE_RELATED_NAME, profile)
        profile.save()


def get_save_slug(extra_field=None):
    '''
    Returns a function to add or make an instance's slug unique

    :param extra_field: field needed in case of a unique_together.
    '''
    if extra_field:
        def save_slug(sender, instance, **kwargs):
            extra_filters = {extra_field: getattr(instance, extra_field)}
            instance.slug = create_or_check_slug(instance, sender, **extra_filters)
    else:
        def save_slug(sender, instance, **kwargs):
            instance.slug = create_or_check_slug(instance, sender)
    return save_slug


pre_save_category_slug = get_save_slug()
pre_save_forum_slug = get_save_slug('category')
pre_save_topic_slug = get_save_slug('forum')


def setup():
    pre_save.connect(pre_save_category_slug, sender=Category)
    pre_save.connect(pre_save_forum_slug, sender=Forum)
    pre_save.connect(pre_save_topic_slug, sender=Topic)
    if settings.PYBB_AUTO_USER_PERMISSIONS:
        post_save.connect(user_saved, sender=get_user_model())
