# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.urlresolvers import reverse
from django.core.validators import validate_email
from django.template.loader import render_to_string
from django.utils import translation

from pybb import util
from pybb.settings import settings

if settings.PYBB_USE_DJANGO_MAILER:
    try:
        from mailer import send_mass_mail
    except ImportError as e:
        raise ImproperlyConfigured('settings.PYBB_USE_DJANGO_MAILER is {0} but mailer could not be imported.'
                                   ' Original exception: {1}'.format(settings.PYBB_USE_DJANGO_MAILER, e.message))
else:
    from django.core.mail import send_mass_mail


def notify_topic_subscribers(post, current_site):
    topic = post.topic
    if post != topic.head:
        old_lang = translation.get_language()

        # Define constants for templates rendering
        delete_url = reverse('pybb:delete_subscription', args=[post.topic.id])
        from_email = django_settings.DEFAULT_FROM_EMAIL

        subject = render_to_string('pybb/mail_templates/subscription_email_subject.html',
                                   {'site': current_site,
                                    'post': post})
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())

        mails = tuple()
        subscribers = topic.subscribers.all()
        if post.user is not None:
            subscribers = subscribers.exclude(pk=post.user.pk)
        for user in subscribers:
            try:
                validate_email(user.email)
            except ValidationError:
                # Invalid email
                continue

            lang = util.get_pybb_profile(user).language or django_settings.LANGUAGE_CODE
            translation.activate(lang)

            message = render_to_string('pybb/mail_templates/subscription_email_body.html',
                                       {'site': current_site,
                                        'post': post,
                                        'delete_url': delete_url,
                                        'user': user})
            mails += ((subject, message, from_email, [user.email]),)

        # Send mails
        send_mass_mail(mails, fail_silently=True)

        # Reactivate previous language
        translation.activate(old_lang)
