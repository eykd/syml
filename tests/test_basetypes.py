import re
import textwrap

import pytest

from syml import basetypes


class TestSource:
    def test_it_should_represent_itself_nicely(self) -> None:
        text = textwrap.dedent(
            """
            - foo
            - bar
            - baz
        """
        )
        source = basetypes.Source.from_text(text, 'foo', filename='foo.txt')
        assert source == basetypes.Source(
            filename='foo.txt',
            start=basetypes.Pos(index=3, line=2, column=2),
            end=basetypes.Pos(index=6, line=2, column=5),
            text='foo',
        )
        assert repr(source) == "<Source: foo.txt, Line 2, Column 2 (index 3): 'foo'>"

    def test_it_should_add_more_text(self) -> None:
        text = textwrap.dedent(
            """
            - foo
            - bar
              baz
        """
        )
        source = basetypes.Source.from_text(text, 'foo', filename='foo.txt')
        new_source = source + '  baz'
        assert new_source is not source
        assert new_source == basetypes.Source(
            filename='foo.txt',
            start=basetypes.Pos(index=3, line=2, column=2),
            end=basetypes.Pos(index=11, line=3, column=5),
            text='foo\n  baz',
        )

    def test_it_should_add_more_source(self) -> None:
        text = textwrap.dedent(
            """
            - foo
            - bar
              baz
            """
        )
        source = basetypes.Source.from_text(text, 'foo', filename='foo.txt')
        source_2 = basetypes.Source.from_text(text, 'baz', filename='foo.txt')
        new_source = source + source_2
        assert new_source is not source
        assert new_source == basetypes.Source(
            filename='foo.txt',
            start=basetypes.Pos(index=3, line=2, column=2),
            end=basetypes.Pos(index=18, line=4, column=5),
            text='foo\nbaz',
        )

    def test_it_should_fail_on_no_substring_match(self) -> None:
        with pytest.raises(ValueError):  # noqa: PT011
            basetypes.Source.from_text('foo', 'bar', filename='blah.txt')

    def test_it_should_fail_to_add_non_source_type(self) -> None:
        source = basetypes.Source.from_text('foo', 'foo', filename='blah.txt')
        with pytest.raises(TypeError):
            source + 5  # type: ignore[operator]


class TestPosFromStrIndex:
    @pytest.fixture
    def text(self) -> str:
        return textwrap.dedent(
            """

            foo
                bar
                    baz blah blargh
            boo
            """
        )

    def test_returns_line_and_column_at_start_of_line(self, text: str) -> None:
        match = re.search('foo', text)
        start = match.start()  # type: ignore[union-attr]
        assert basetypes.Pos.from_str_index(text, start) == basetypes.Pos(start, 3, 0)

    def test_returns_line_and_column_of_indented_text(self, text: str) -> None:
        match = re.search('bar', text)
        start = match.start()  # type: ignore[union-attr]
        assert basetypes.Pos.from_str_index(text, start) == basetypes.Pos(start, 4, 4)

    def test_returns_line_and_column_of_midline_text(self, text: str) -> None:
        match = re.search('blah', text)
        start = match.start()  # type: ignore[union-attr]
        assert basetypes.Pos.from_str_index(text, start) == basetypes.Pos(start, 5, 12)

    def test_returns_last_line_and_first_column_of_bad_index(self, text: str) -> None:
        assert basetypes.Pos.from_str_index(text, len(text) + 5) == basetypes.Pos(len(text), 6, 0)
