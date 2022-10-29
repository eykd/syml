import re
import textwrap

import pytest

from syml import types


class TestSource:
    def test_it_should_represent_itself_nicely(self):
        text = textwrap.dedent(
            """
            - foo
            - bar
            - baz
        """
        )
        source = types.Source.from_text(text, "foo", filename="foo.txt")
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
        source = types.Source.from_text(text, "foo", filename="foo.txt")
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
        source = types.Source.from_text(text, "foo", filename="foo.txt")
        source_2 = types.Source.from_text(text, "\n  baz", filename="foo.txt")
        new_source = source + source_2
        assert new_source is not source
        assert new_source == types.Source(
            filename="foo.txt",
            start=types.Pos(index=3, line=2, column=2),
            end=types.Pos(index=12, line=4, column=5),
            text="foo\n  baz",
            value="foo\n  baz",
        )


class TestPosFromStrIndex:
    @pytest.fixture
    def text(self):
        return textwrap.dedent(
            """

        foo
            bar
                baz blah blargh
        boo
        """
        )

    def test_returns_line_and_column_at_start_of_line(self, text):
        match = re.search("foo", text)
        start = match.start()
        assert types.Pos.from_str_index(text, start) == types.Pos(start, 3, 0)

    def test_returns_line_and_column_of_indented_text(self, text):
        match = re.search("bar", text)
        start = match.start()
        assert types.Pos.from_str_index(text, start) == types.Pos(start, 4, 4)

    def test_returns_line_and_column_of_midline_text(self, text):
        match = re.search("blah", text)
        start = match.start()
        assert types.Pos.from_str_index(text, start) == types.Pos(start, 5, 12)

    def test_returns_last_line_and_first_column_of_bad_index(self, text):
        assert types.Pos.from_str_index(text, len(text) + 5) == types.Pos(len(text), 6, 0)
