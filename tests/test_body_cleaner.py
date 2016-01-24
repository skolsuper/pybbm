# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import pytest

from pybb import util
from pybb.cleaners import rstrip_str

cleaners_map = [
    ['pybb.cleaners.filter_blanks', 'some\n\n\n\ntext\n\nwith\nnew\nlines', 'some\ntext\n\nwith\nnew\nlines'],
    [rstrip_str, 'text    \n    \nwith whitespaces     ', 'text\n\nwith whitespaces'],
]


@pytest.mark.parametrize(*cleaners_map)
def test_body_cleaners(cleaner, source, expected):
    assert util.get_body_cleaner(cleaner)(source) == expected
