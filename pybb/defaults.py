# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import warnings


# TODO In a near future, this code will be deleted when callable settings will not supported anymore.
callable_warning = ('%(setting_name)s should not be a callable anymore but a path to the parser classes.'
                    'ex : myproject.markup.CustomBBCodeParser. It will stop working in next pybbm release.')
wrong_setting_warning = ('%s setting will be removed in next pybbm version. '
                         'Place your custom quote functions in markup class and override '
                         'PYBB_MARKUP_ENGINES_PATHS/PYBB_MARKUP settings')
bad_function_warning = '%(bad)s function is deprecated. Use %(good)s instead.'

def bbcode(s):
    warnings.warn(
        bad_function_warning % {
            'bad': 'pybb.defaults.bbcode',
            'good': 'pybb.markup.bbcode.BBCodeParser',
        },
        DeprecationWarning)
    from pybb.markup.bbcode import BBCodeParser

    return BBCodeParser().format(s)


def markdown(s):
    warnings.warn(
        bad_function_warning % {
            'bad': 'pybb.defaults.markdown',
            'good': 'pybb.markup.markdown.MarkdownParser',
        },
        DeprecationWarning)
    from pybb.markup.markdown import MarkdownParser

    return MarkdownParser().format(s)


def _render_quote(name, value, options, parent, context):
    warnings.warn('pybb.defaults._render_quote function is deprecated. '
                  'This function is internal of new pybb.markup.bbcode.BBCodeParser class.',
                  DeprecationWarning)
    from pybb.markup.bbcode import BBCodeParser

    return BBCodeParser()._render_quote(name, value, options, parent, context)


def smile_it(s):
    warnings.warn(
        bad_function_warning % {
            'bad': 'pybb.defaults.smile_it',
            'good': 'pybb.markup.base.smile_it',
        },
        DeprecationWarning)
    from pybb.markup.base import smile_it as real_smile_it

    return real_smile_it(s)
