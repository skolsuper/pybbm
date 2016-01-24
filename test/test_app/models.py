from __future__ import unicode_literals

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models

from pybb.profiles import PybbProfile


class CustomProfile(PybbProfile):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name='linked account',
        related_name='pybb_customprofile',
        blank=False, null=False,
    )

    class Meta(object):
        verbose_name = 'Profile'
        verbose_name_plural = 'Profiles'

    def get_absolute_url(self):
        return reverse('pybb:user', kwargs={'username': self.user.get_username()})

    def get_display_name(self):
        return self.user.get_username()
