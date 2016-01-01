# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.test import TestCase

from pybb import util, defaults
from pybb.tests.utils import SharedTestModule

User = get_user_model()


class MarkupParserTest(TestCase, SharedTestModule):

    def setUp(self):
        # Reinit Engines because they are stored in memory and the current bbcode engine stored
        # may be the old one, depending the test order exec.
        self.ORIG_PYBB_MARKUP_ENGINES = util.PYBB_MARKUP_ENGINES
        self.ORIG_PYBB_QUOTE_ENGINES = util.PYBB_QUOTE_ENGINES
        util.PYBB_MARKUP_ENGINES = {
            'bbcode': 'pybb.markup.bbcode.BBCodeParser',  # default parser
            'bbcode_custom': 'test_project.markup_parsers.CustomBBCodeParser',  # overrided default parser
            'liberator': 'test_project.markup_parsers.LiberatorParser',  # completely new parser
            'fake': 'pybb.markup.base.BaseParser',  # base parser
            'markdown': defaults.markdown  # old-style callable parser,
        }
        util.PYBB_QUOTE_ENGINES = {
            'bbcode': 'pybb.markup.bbcode.BBCodeParser',  # default parser
            'bbcode_custom': 'test_project.markup_parsers.CustomBBCodeParser',  # overrided default parser
            'liberator': 'test_project.markup_parsers.LiberatorParser',  # completely new parser
            'fake': 'pybb.markup.base.BaseParser',  # base parser
            'markdown': lambda text, username="": '>' + text.replace('\n', '\n>').replace('\r', '\n>') + '\n'  # old-style callable parser
        }

    def tearDown(self):
        util._MARKUP_ENGINES = {}
        util._QUOTE_ENGINES = {}
        util.PYBB_MARKUP_ENGINES = self.ORIG_PYBB_MARKUP_ENGINES
        util.PYBB_QUOTE_ENGINES = self.ORIG_PYBB_QUOTE_ENGINES

    def test_markup_engines(self):

        def _test_engine(parser_name, text_to_html_map):
            for item in text_to_html_map:
                self.assertIn(util._get_markup_formatter(parser_name)(item[0]), item[1:])

        text_to_html_map = [
            ['[b]bold[/b]', '<strong>bold</strong>'],
            ['[i]italic[/i]', '<em>italic</em>'],
            ['[u]underline[/u]', '<u>underline</u>'],
            ['[s]striked[/s]', '<strike>striked</strike>'],
            [
                '[img]http://domain.com/image.png[/img]',
                '<img src="http://domain.com/image.png"></img>',
                '<img src="http://domain.com/image.png">'
            ],
            ['[url=google.com]search in google[/url]', '<a href="http://google.com">search in google</a>'],
            ['http://google.com', '<a href="http://google.com">http://google.com</a>'],
            ['[list][*]1[*]2[/list]', '<ul><li>1</li><li>2</li></ul>'],
            [
                '[list=1][*]1[*]2[/list]',
                '<ol><li>1</li><li>2</li></ol>',
                '<ol style="list-style-type:decimal;"><li>1</li><li>2</li></ol>'
            ],
            ['[quote="post author"]quote[/quote]', '<blockquote><em>post author</em><br>quote</blockquote>'],
            [
                '[code]code[/code]',
                '<div class="code"><pre>code</pre></div>',
                '<pre><code>code</code></pre>']
            ,
        ]
        _test_engine('bbcode', text_to_html_map)

        text_to_html_map = text_to_html_map + [
            ['[ul][li]1[/li][li]2[/li][/ul]', '<ul><li>1</li><li>2</li></ul>'],
            [
                '[youtube]video_id[/youtube]',
                (
                    '<iframe src="http://www.youtube.com/embed/video_id?wmode=opaque" '
                    'data-youtube-id="video_id" allowfullscreen="" frameborder="0" '
                    'height="315" width="560"></iframe>'
                )
            ],
        ]
        _test_engine('bbcode_custom', text_to_html_map)

        text_to_html_map = [
            ['Windows and Mac OS are wonderfull OS !', 'GNU Linux and FreeBSD are wonderfull OS !'],
            ['I love PHP', 'I love Python'],
        ]
        _test_engine('liberator', text_to_html_map)

        text_to_html_map = [
            ['[b]bold[/b]', '[b]bold[/b]'],
            ['*italic*', '*italic*'],
        ]
        _test_engine('fake', text_to_html_map)
        _test_engine('not_existent', text_to_html_map)

        text_to_html_map = [
            ['**bold**', '<p><strong>bold</strong></p>'],
            ['*italic*', '<p><em>italic</em></p>'],
            [
                '![alt text](http://domain.com/image.png title)',
                '<p><img alt="alt text" src="http://domain.com/image.png" title="title" /></p>'
            ],
            [
                '[search in google](https://www.google.com)',
                '<p><a href="https://www.google.com">search in google</a></p>'
            ],
            [
                '[google] some text\n[google]: https://www.google.com',
                '<p><a href="https://www.google.com">google</a> some text</p>'
            ],
            ['* 1\n* 2', '<ul>\n<li>1</li>\n<li>2</li>\n</ul>'],
            ['1. 1\n2. 2', '<ol>\n<li>1</li>\n<li>2</li>\n</ol>'],
            ['> quote', '<blockquote>\n<p>quote</p>\n</blockquote>'],
            ['```\ncode\n```', '<p><code>code</code></p>'],
        ]
        _test_engine('markdown', text_to_html_map)

    def test_quote_engines(self):

        def _test_engine(parser_name, text_to_quote_map):
            for item in text_to_quote_map:
                self.assertEqual(util._get_markup_quoter(parser_name)(item[0]), item[1])
                self.assertEqual(util._get_markup_quoter(parser_name)(item[0], 'username'), item[2])

        text_to_quote_map = [
            ['quote text', '[quote=""]quote text[/quote]\n', '[quote="username"]quote text[/quote]\n']
        ]
        _test_engine('bbcode', text_to_quote_map)
        _test_engine('bbcode_custom', text_to_quote_map)

        text_to_quote_map = [
            ['quote text', 'quote text', 'posted by: username\nquote text']
        ]
        _test_engine('liberator', text_to_quote_map)

        text_to_quote_map = [
            ['quote text', 'quote text', 'quote text']
        ]
        _test_engine('fake', text_to_quote_map)
        _test_engine('not_existent', text_to_quote_map)

        text_to_quote_map = [
            ['quote\r\ntext', '>quote\n>\n>text\n', '>quote\n>\n>text\n']
        ]
        _test_engine('markdown', text_to_quote_map)

    def test_body_cleaners(self):
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        staff = User.objects.create_user('staff', 'staff@localhost', 'staff')
        staff.is_staff = True
        staff.save()

        from pybb.markup.base import rstrip_str
        cleaners_map = [
            ['pybb.markup.base.filter_blanks', 'some\n\n\n\ntext\n\nwith\nnew\nlines', 'some\ntext\n\nwith\nnew\nlines'],
            [rstrip_str, 'text    \n    \nwith whitespaces     ', 'text\n\nwith whitespaces'],
        ]
        for cleaner, source, dest in cleaners_map:
            self.assertEqual(util.get_body_cleaner(cleaner)(user, source), dest)
            self.assertEqual(util.get_body_cleaner(cleaner)(staff, source), source)
