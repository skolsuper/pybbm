from django.contrib.auth import get_user_model
from django.test import TestCase

from pybb import util
from pybb.settings import settings as pybb_settings

User = get_user_model()


class ProfileCreateTest(TestCase):

    def test_profile_autocreation_signal_on(self):
        user = User.objects.create_user('cronos', 'cronos@localhost', 'cronos')
        profile = getattr(user, pybb_settings.PYBB_PROFILE_RELATED_NAME, None)
        self.assertIsNotNone(profile)
        self.assertIsInstance(profile, util.get_pybb_profile_model())

    def test_profile_autocreation_middleware(self):
        user = User.objects.create_user('cronos', 'cronos@localhost', 'cronos')
        getattr(user, pybb_settings.PYBB_PROFILE_RELATED_NAME).delete()
        #just display a page : the middleware should create the profile
        self.client.login(username='cronos', password='cronos')
        self.client.get('/')
        user = User.objects.get(username='cronos')
        profile = getattr(user, pybb_settings.PYBB_PROFILE_RELATED_NAME, None)
        self.assertIsNotNone(profile)
        self.assertIsInstance(profile, util.get_pybb_profile_model())
