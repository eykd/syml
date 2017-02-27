import textwrap
from unittest import TestCase
from ensure import ensure

from syml import utils


class SourceTests(TestCase):
    def test_it_should_represent_itself_nicely(self):
        text = textwrap.dedent("""
            - foo
            - bar
            - baz
        """)
        source = utils.get_text_source(text, 'foo', filename='foo.txt')
        (ensure(repr(source))
         .equals("foo.txt, Line 2, Column 2 (index 3): 'foo' ('foo')"))
