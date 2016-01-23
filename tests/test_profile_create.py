import pytest

from pybb import util
from pybb.settings import settings


@pytest.mark.django_db
def test_profile_autocreation_signal_on(django_user_model):
    user = django_user_model.objects.create_user('cronos', 'cronos@localhost', 'cronos')
    profile = getattr(user, settings.PYBB_PROFILE_RELATED_NAME, None)
    assert profile is not None
    assert isinstance(profile, util.get_pybb_profile_model())


@pytest.mark.django_db
def test_profile_autocreation_middleware(django_user_model, client):
    user = django_user_model.objects.create_user('cronos', 'cronos@localhost', 'cronos')
    getattr(user, settings.PYBB_PROFILE_RELATED_NAME).delete()
    #just display a page : the middleware should create the profile
    client.login(username='cronos', password='cronos')
    client.get('/')
    user = django_user_model.objects.get(username='cronos')
    profile = getattr(user, settings.PYBB_PROFILE_RELATED_NAME, None)
    assert profile is not None
    assert isinstance(profile, util.get_pybb_profile_model())
