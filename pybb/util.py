# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.module_loading import import_string
from django.utils.six import string_types
from django.utils.translation import ugettext as _

from pybb.compat import slugify, get_related_model_class
from pybb.markup.base import BaseParser
from pybb.settings import settings

_MARKUP_ENGINES = {}


def get_markup_engine(name=None):
    """
    Returns the named markup engine instance, or the default one if name is not given.
    This function will replace _get_markup_formatter and _get_markup_quoter in the
    next major release.
    """
    name = name or settings.PYBB_MARKUP
    engine = _MARKUP_ENGINES.get(name)
    if engine:
        return engine
    engines_dict = settings.PYBB_MARKUP_ENGINES_PATHS
    if name not in engines_dict:
        engine = BaseParser()
    else:
        engine = engines_dict[name]
        # TODO In a near future, we should stop to support callable
        if isinstance(engine, string_types):
            # This is a path, import it
            engine = import_string(engine)()
    _MARKUP_ENGINES[name] = engine
    return engine


def get_body_cleaner(name):
    return import_string(name) if isinstance(name, string_types) else name


def unescape(text):
    """
    Do reverse escaping.
    """
    escape_map = [('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'), ('&quot;', '"'), ('&#39;', '\'')]
    for escape_values in escape_map:
        text = text.replace(*escape_values)
    return text


def get_pybb_profile(user):
    from pybb import settings as defaults

    if not user.is_authenticated():
        if defaults.settings.PYBB_ENABLE_ANONYMOUS_POST:
            User = get_user_model()
            user = User.objects.get(**{User.USERNAME_FIELD: defaults.settings.PYBB_ANONYMOUS_USERNAME})
        else:
            raise ValueError(_('Can\'t get profile for anonymous user'))

    if defaults.settings.PYBB_PROFILE_RELATED_NAME:
        return getattr(user, defaults.settings.PYBB_PROFILE_RELATED_NAME)
    else:
        return user


def get_pybb_profile_model():
    from pybb import settings as defaults

    if defaults.settings.PYBB_PROFILE_RELATED_NAME:
        return get_related_model_class(get_user_model(), defaults.settings.PYBB_PROFILE_RELATED_NAME)
    else:
        return get_user_model()


def build_cache_key(key_name, **kwargs):
    if key_name == 'anonymous_topic_views':
        return 'pybbm_anonymous_topic_%s_views' % kwargs['topic_id']
    else:
        raise ValueError('Wrong key_name parameter passed: %s' % key_name)


class FilePathGenerator(object):
    """
    Special class for generating random filenames
    Can be deconstructed for correct migration
    """

    def __init__(self, to, *args, **kwargs):
        self.to = to

    def deconstruct(self, *args, **kwargs):
        return 'pybb.util.FilePathGenerator', [], {'to': self.to}

    def __call__(self, instance, filename):
        """
        This function generate filename with uuid4
        it's useful if:
        - you don't want to allow others to see original uploaded filenames
        - users can upload images with unicode in filenames wich can confuse browsers and filesystem
        """
        ext = filename.split('.')[-1]
        filename = "%s.%s" % (uuid.uuid4(), ext)
        return os.path.join(self.to, filename)


def create_or_check_slug(instance, model, **extra_filters):
    """
    returns a unique slug

    :param instance : target instance
    :param model: needed as instance._meta.model is available since django 1.6
    :param extra_filters: filters needed for Forum and Topic for their unique_together field
    """
    initial_slug = instance.slug or slugify(instance.name)
    count = -1
    last_count_len = 0
    slug_is_not_unique = True
    while slug_is_not_unique:
        count += 1

        if count >= settings.PYBB_NICE_URL_SLUG_DUPLICATE_LIMIT:
            msg = _('After {limit} attempts, there is not any unique slug value for "{slug}"')
            raise ValidationError(msg.format(limit=settings.PYBB_NICE_URL_SLUG_DUPLICATE_LIMIT, slug=initial_slug))

        count_len = len(str(count))

        if last_count_len != count_len:
            last_count_len = count_len
            filters = {'slug__startswith': initial_slug[:(254-count_len)], }
            if extra_filters:
                filters.update(extra_filters)
            objs = model.objects.filter(**filters).exclude(pk=instance.pk)
            slug_list = [obj.slug for obj in objs]

        if count == 0:
            slug = initial_slug
        else:
            slug = '%s-%d' % (initial_slug[:(254-count_len)], count)
        slug_is_not_unique = slug in slug_list

    return slug
