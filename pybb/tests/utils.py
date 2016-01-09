from django.contrib.auth import get_user_model

from pybb import util

User = get_user_model()
Profile = util.get_pybb_profile_model()
username_field = User.USERNAME_FIELD
__author__ = 'zeus'
