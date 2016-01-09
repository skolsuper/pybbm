# coding=utf-8
from __future__ import unicode_literals

import django
from django.utils.encoding import force_text
from unidecode import unidecode


def get_image_field_class():
    try:
        from sorl.thumbnail import ImageField
    except ImportError:
        from django.db.models import ImageField
    return ImageField


def get_image_field_full_name():
    try:
        from sorl.thumbnail import ImageField
        name = 'sorl.thumbnail.fields.ImageField'
    except ImportError:
        from django.db.models import ImageField
        name = 'django.db.models.fields.files.ImageField'
    return name


def get_atomic_func():
    try:
        from django.db.transaction import atomic as atomic_func
    except ImportError:
        from django.db.transaction import commit_on_success as atomic_func
    return atomic_func


def get_related_model_class(parent_model, field_name):
    if django.VERSION[:2] < (1, 8):
        return getattr(parent_model, field_name).related.model
    else:
        return parent_model._meta.get_field(field_name).related_model


def slugify(text):
    """
    Slugify function that supports unicode symbols
    :param text: any unicode text
    :return: slugified version of passed text
    """
    if django.VERSION[:2] < (1, 5):
        from django.template.defaultfilters import slugify as django_slugify
    else:
        from django.utils.text import slugify as django_slugify

    return django_slugify(force_text(unidecode(text)))
