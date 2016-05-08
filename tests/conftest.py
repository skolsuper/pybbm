import pytest
from django.db import connection


@pytest.fixture()
def precision_time():
    """Check database time precision is high enough for test"""
    if not getattr(connection.features, 'supports_microsecond_precision', False):
        pytest.skip('Database time precision not high enough')


@pytest.fixture()
def api_client():
    """A DRF test client instance."""

    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture()
def user():
    from django.contrib.auth.models import User
    return User.objects.create_user('zeus', 'zeus@localhost', 'zeus')


@pytest.fixture()
def category(db):
    from pybb.models.category import Category
    return Category.objects.create(name='foo')


@pytest.fixture()
def forum(db, category):
    from pybb.models.forum import Forum
    return Forum.objects.create(name='xfoo', description='bar', category=category)


@pytest.fixture()
def topic(db, forum, user):
    from pybb.models.topic import Topic
    return Topic.objects.create(name='xtopic', forum=forum, user=user)
