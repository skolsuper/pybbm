import os

from django.conf import settings as django_settings

defaults = {
    'PYBB_DEFAULT_TOPICS_PER_PAGE': 50,
    'PYBB_DEFAULT_POSTS_PER_PAGE': 10,
    'PYBB_MAX_TOPICS_PER_PAGE': 100,
    'PYBB_MAX_POSTS_PER_PAGE': 100,

    'PYBB_AVATAR_WIDTH': 80,
    'PYBB_AVATAR_HEIGHT': 80,
    'PYBB_MAX_AVATAR_SIZE': 1024 * 50,

    'PYBB_DEFAULT_TIME_ZONE': 3,

    'PYBB_SIGNATURE_MAX_LENGTH': 1024,
    'PYBB_SIGNATURE_MAX_LINES': 3,

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

    'PYBB_BODY_CLEANERS': ['pybb.cleaners.rstrip_str', 'pybb.cleaners.filter_blanks'],
    'PYBB_BODY_VALIDATOR': None,
    'PYBB_POLL_MAX_ANSWERS': 10,
    'PYBB_AUTO_USER_PERMISSIONS': True,
    'PYBB_USE_DJANGO_MAILER': False,
    'PYBB_PERMISSION_HANDLER': 'pybb.permissions.DefaultPermissionHandler',
    'PYBB_PROFILE_RELATED_NAME': 'pybb_profile',
    'PYBB_INITIAL_CUSTOM_USER_MIGRATION': None,
}


class SettingsObject(object):

    def __getattr__(self, item):
        return getattr(django_settings, item, defaults[item])

settings = SettingsObject()
