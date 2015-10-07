import os
import warnings

from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.six import string_types

defaults = {
    'PYBB_TOPIC_PAGE_SIZE': 10,
    'PYBB_FORUM_PAGE_SIZE': 20,

    'PYBB_AVATAR_WIDTH': 80,
    'PYBB_AVATAR_HEIGHT': 80,
    'PYBB_MAX_AVATAR_SIZE': 1024 * 50,

    'PYBB_DEFAULT_TIME_ZONE': 3,

    'PYBB_SIGNATURE_MAX_LENGTH': 1024,
    'PYBB_SIGNATURE_MAX_LINES': 3,

    'PYBB_DEFAULT_MARKUP': 'bbcode',
    'PYBB_FREEZE_FIRST_POST': False,

    'PYBB_ATTACHMENT_SIZE_LIMIT': 1024 * 1024,
    'PYBB_ATTACHMENT_ENABLE': False,
    'PYBB_ATTACHMENT_UPLOAD_TO': os.path.join('pybb_upload', 'attachments'),

    'PYBB_DEFAULT_AVATAR_URL': 'pybb/img/default_avatar.jpg',
    'PYBB_DEFAULT_TITLE': 'PYBB Powered Forum',
    'PYBB_SMILES_PREFIX': 'pybb/emoticons/',
    'PYBB_SMILES': {
        '&gt;_&lt;': 'angry.png',
        ':.(': 'cry.png',
        'o_O': 'eyes.png',
        '[]_[]': 'geek.png',
        '8)': 'glasses.png',
        ':D': 'lol.png',
        ':(': 'sad.png',
        ':O': 'shok.png',
        '-_-': 'shy.png',
        ':)': 'smile.png',
        ':P': 'tongue.png',
        ';)': 'wink.png'
    },

    'PYBB_NICE_URL': False,
    'PYBB_NICE_URL_PERMANENT_REDIRECT': True,
    'PYBB_NICE_URL_SLUG_DUPLICATE_LIMIT': 100,

    'PYBB_TEMPLATE': "base.html",
    'PYBB_DEFAULT_AUTOSUBSCRIBE': True,
    'PYBB_ENABLE_ANONYMOUS_POST': False,
    'PYBB_ANONYMOUS_USERNAME': 'Anonymous',
    'PYBB_ANONYMOUS_VIEWS_CACHE_BUFFER': 100,

    'PYBB_DISABLE_SUBSCRIPTIONS': False,
    'PYBB_DISABLE_NOTIFICATIONS': False,
    'PYBB_NOTIFY_ON_EDIT': True,
    'PYBB_PREMODERATION': False,

    'PYBB_BODY_VALIDATOR': None,
    'PYBB_POLL_MAX_ANSWERS': 10,
    'PYBB_AUTO_USER_PERMISSIONS': True,
    'PYBB_USE_DJANGO_MAILER': False,
    'PYBB_PERMISSION_HANDLER': 'pybb.permissions.DefaultPermissionHandler',
    'PYBB_PROFILE_RELATED_NAME': 'pybb_profile',
    'PYBB_INITIAL_CUSTOM_USER_MIGRATION': None,
}

# defaults['TODO']In a near future, this code will be deleted when callable django_settings will not supported anymore.
callable_warning = ('%(setting_name)s should not be a callable anymore but a path to the parser classes.'
                    'ex : myproject.markup.CustomBBCodeParser. It will stop working in next pybbm release.')
wrong_setting_warning = ('%s setting will be removed in next pybbm version. '
                         'Place your custom quote functions in markup class and override '
                         'PYBB_MARKUP_ENGINES_PATHS/PYBB_MARKUP settings')
bad_function_warning = '%(bad)s function is deprecated. Use %(good)s instead.'


def getsetting_with_deprecation_check(all_django_settings, setting_name):
    setting_value = getattr(all_django_settings, setting_name)
    values = setting_value if type(setting_value) is not dict else setting_value.values()
    for value in values:
        if isinstance(value, string_types):
            continue
        warnings.warn(
            callable_warning % {'setting_name': setting_name, },
            DeprecationWarning
        )
    return setting_value


if not hasattr(django_settings, 'PYBB_MARKUP_ENGINES_PATHS'):
    defaults['PYBB_MARKUP_ENGINES_PATHS'] = {
        'bbcode': 'pybb.markup.bbcode.BBCodeParser', 'markdown': 'pybb.markup.markdown.MarkdownParser'}
else:
    defaults['PYBB_MARKUP_ENGINES_PATHS'] = getattr(django_settings, 'PYBB_MARKUP_ENGINES_PATHS')

# defaults['TODO']in the next major release : delete defaults['PYBB_MARKUP_ENGINES']and defaults['PYBB_QUOTE_ENGINES']django_settings
if not hasattr(django_settings, 'PYBB_MARKUP_ENGINES'):
    defaults['PYBB_MARKUP_ENGINES'] = defaults['PYBB_MARKUP_ENGINES_PATHS']
else:
    warnings.warn(wrong_setting_warning % 'PYBB_MARKUP_ENGINES', DeprecationWarning)
    defaults['PYBB_MARKUP_ENGINES'] = getsetting_with_deprecation_check(django_settings, 'PYBB_MARKUP_ENGINES')

if not hasattr(django_settings, 'PYBB_QUOTE_ENGINES'):
    defaults['PYBB_QUOTE_ENGINES'] = defaults['PYBB_MARKUP_ENGINES_PATHS']
else:
    warnings.warn(wrong_setting_warning % 'PYBB_QUOTE_ENGINES', DeprecationWarning)
    defaults['PYBB_QUOTE_ENGINES'] = getsetting_with_deprecation_check(django_settings, 'PYBB_QUOTE_ENGINES')

defaults['PYBB_MARKUP'] = None
if not defaults['PYBB_MARKUP'] or defaults['PYBB_MARKUP'] not in defaults['PYBB_MARKUP_ENGINES']:
    if not defaults['PYBB_MARKUP_ENGINES']:
        warnings.warn('There is no markup engines defined in your django_settings. '
                      'Default pybb.base.BaseParser will be used.'
                      'Please set correct PYBB_MARKUP_ENGINES_PATHS and PYBB_MARKUP settings.',
                      DeprecationWarning)
        defaults['PYBB_MARKUP'] = None
    elif 'bbcode' in defaults['PYBB_MARKUP_ENGINES']:
        # Backward compatibility. bbcode is the default markup
        defaults['PYBB_MARKUP'] = 'bbcode'
    else:
        raise ImproperlyConfigured('PYBB_MARKUP must be defined to an existing key of '
                                   'PYBB_MARKUP_ENGINES_PATHS')

if not hasattr(django_settings, 'PYBB_BODY_CLEANERS'):
    defaults['PYBB_BODY_CLEANERS'] = ['pybb.markup.base.rstrip_str', 'pybb.markup.base.filter_blanks']
else:
    defaults['PYBB_BODY_CLEANERS'] = getsetting_with_deprecation_check(django_settings, 'PYBB_BODY_CLEANERS')


class SettingsObject(object):

    def __getattr__(self, item):
        return getattr(django_settings, item, defaults[item])

settings = SettingsObject()
