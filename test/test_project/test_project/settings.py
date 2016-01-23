# coding=utf-8
from __future__ import unicode_literals

import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DEBUG = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'TEST_CHARSET': 'utf8',
    }
}
test_db = os.environ.get('DB', 'sqlite')
if test_db == 'mysql':
    DATABASES['default'].update({
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'pybbm',
        'USER': 'root',
        'TEST_COLLATION': 'utf8_general_ci',
    })
elif test_db == 'postgres':
    DATABASES['default'].update({
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'USER': 'postgres',
        'NAME': 'pybbm',
        'OPTIONS': {}
    })

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'test_app',
    'pybb'
]

SECRET_KEY = 'some secret'

TEMPLATE_CONTEXT_PROCESSORS = [
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.request',
    'django.core.context_processors.tz'
]

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'pybb.middleware.PybbMiddleware',
)

ROOT_URLCONF = 'test_project.urls'

SITE_ID = 1

STATIC_URL = '/static/'

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'templates'),
)

LOGIN_URL = '/'

PYBB_ATTACHMENT_ENABLE = True
PYBB_PROFILE_RELATED_NAME = 'pybb_customprofile'

REST_FRAMEWORK = {
    'TEST_REQUEST_DEFAULT_FORMAT': 'json'
}
