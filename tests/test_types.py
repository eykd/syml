import textwrap
from unittest import TestCase

from syml import types, utils


class SourceTests(TestCase):
    def test_it_should_represent_itself_nicely(self):
        text = textwrap.dedent(
            """
            - foo
            - bar
            - baz
        """
        )
        source = utils.get_text_source(text, "foo", filename="foo.txt")
        assert source == types.Source(
            filename="foo.txt",
            start=types.Pos(index=3, line=2, column=2),
            end=types.Pos(index=6, line=2, column=5),
            text="foo",
            value="foo",
        )
        assert repr(source) == "foo.txt, Line 2, Column 2 (index 3): 'foo' ('foo')"

    def test_it_should_add_more_text(self):
        text = textwrap.dedent(
            """
            - foo
            - bar
              baz
        """
        )
        source = utils.get_text_source(text, "foo", filename="foo.txt")
        new_source = source + "\n  baz"
        assert new_source is not source
        assert new_source == types.Source(
            filename="foo.txt",
            start=types.Pos(index=3, line=2, column=2),
            end=types.Pos(index=12, line=4, column=5),
            text="foo\n  baz",
            value="foo\n  baz",
        )

    def test_it_should_add_more_source(self):
        text = textwrap.dedent(
            """
            - foo
            - bar
              baz
        """
        )
        source = utils.get_text_source(text, "foo", filename="foo.txt")
        source_2 = utils.get_text_source(text, "\n  baz", filename="foo.txt")
        new_source = source + source_2
        assert new_source is not source
        assert new_source == types.Source(
            filename="foo.txt",
            start=types.Pos(index=3, line=2, column=2),
            end=types.Pos(index=12, line=4, column=5),
            text="foo\n  baz",
            value="foo\n  baz",
        )
