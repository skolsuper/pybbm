import pytest


@pytest.fixture()
def api_client():
    """A Django test client instance."""

    from rest_framework.test import APIClient

    return APIClient()
