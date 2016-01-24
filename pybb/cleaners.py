# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from django.conf import settings

from pybb.settings import settings as pybb_settings


def smile_it(s):
    for smile, url in pybb_settings.PYBB_SMILES.items():
        s = s.replace(smile, '<img src="%s%s%s" alt="smile" />' % (settings.STATIC_URL, pybb_settings.PYBB_SMILES_PREFIX, url))
    return s


def filter_blanks(str):
    """
    Replace more than 3 blank lines with only 1 blank line
    """
    return re.sub(r'\n{2}\n+', '\n', str)


def rstrip_str(str):
    """
    Replace strings with spaces (tabs, etc..) only with newlines
    Remove blank line at the end
    """
    return '\n'.join([s.rstrip() for s in str.splitlines()])
