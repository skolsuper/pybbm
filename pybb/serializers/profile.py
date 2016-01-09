# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import serializers

from pybb.util import get_pybb_profile_model

Profile = get_pybb_profile_model()


class ProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = Profile
        fields = ('display_name', 'avatar', 'signature')

    display_name = serializers.CharField(source='get_display_name')
