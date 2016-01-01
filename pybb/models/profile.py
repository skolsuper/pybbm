# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from annoying.fields import AutoOneToOneField
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from pybb.profiles import PybbProfile


class Profile(PybbProfile):
    """
    Profile class that can be used if you doesn't have
    your site profile.
    """

    class Meta(object):
        verbose_name = _('Profile')
        verbose_name_plural = _('Profiles')
        app_label = 'pybb'

    user = AutoOneToOneField(settings.AUTH_USER_MODEL, related_name='pybb_profile', verbose_name=_('User'))

    def get_absolute_url(self):
        return reverse('pybb:user', kwargs={'username': self.user.get_username()})

    def get_display_name(self):
        return self.user.get_username()
