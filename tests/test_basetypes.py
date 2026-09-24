import re
import textwrap

import pytest
from parsimonious.expressions import Literal
from parsimonious.nodes import Node

from syml import basetypes, parsers
from syml.preprocess import PositionMap


class TestSourceFromNodeOriginalTextCoordinates:
    """Contract 08 §Original-text coordinates (FR-013, R-02).

    `Source.from_node(pnode, line, position_map, filename)` must build each
    endpoint as `position_map.to_original(pos_at(line, offset))`, so a BOM at
    the front of the document shifts reported positions by one — not the
    normalized-text position `Pos.from_str_index` reports today.
    """

    def test_it_should_map_endpoints_through_pos_at_and_to_original(self) -> None:
        normalized = 'key: value'
        pnode = Node(Literal('value'), normalized, 5, 10)
        line = basetypes.Line(text=normalized, start=0, number=1)
        position_map = PositionMap(bom_offset=1, crlf_indices=())

        source = basetypes.Source.from_node(pnode, line, position_map, filename='doc.syml')

        assert source.start == basetypes.Pos(index=6, line=1, column=6)
        assert source.end == basetypes.Pos(index=11, line=1, column=11)
        assert source.text == 'value'


class TestSource:
    def test_it_should_work_interchangeably_as_a_dict_key_with_comparable_string(self) -> None:
        text = 'foo'
        source = basetypes.Source.from_text(text, 'foo')
        data = {source: 'bar'}
        assert data['foo'] == 'bar'  # type: ignore[index]

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

    def test_it_should_not_equal_non_str_operands_by_stringified_value(self) -> None:
        """Contract 08 §Equality and hashing (§10.3, R-07).

        `__eq__` must compare with `str`s and `Source`s only, returning
        `NotImplemented` for any other type instead of falling back to
        `str(self) == str(other)`. A `Source('1')` must not equal the `int`
        `1`, even though `str(1) == '1'`.
        """
        source = basetypes.Source.from_text('1', '1')
        assert source != 1
        assert 1 != source  # noqa: SIM300


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

    def test_it_should_count_lines_by_lf_only_not_unicode_line_breaks(self) -> None:
        text = 'a: b\u2028c\nx: y'
        index = text.index('x')
        assert basetypes.Pos.from_str_index(text, index) == basetypes.Pos(index, 2, 0)


class TestQuotedValueSpanReporting:
    """Contract 08 \u00a7Quoted-value spans.

    `start` is the opening quote and `end` is just past the closing quote
    (exclusive, before any trailing ` *`) \u2014 both in the *original* text's
    coordinates (\u00a7 Original-text coordinates), not the CRLF-normalized text
    the grammar actually parses. `text` is the decoded value, so its length
    need not match the raw token's.
    """

    def test_it_should_report_the_original_text_span_of_a_quoted_value_on_a_crlf_line(self) -> None:
        original = "a: b\r\nk: 'it''s' \n"
        tree = parsers.parse(original, filename='doc.syml')

        source = tree.as_source()['k']

        assert source.text == "it's"
        assert source.start.index == 9
        assert source.end.index == 16
        assert original[source.start.index : source.end.index] == "'it''s'"


class TestContinuationSpanReporting:
    """Contract 08 §Continuation spans.

    A multiline `TextLeafNode`'s `Source` keeps `start` at the value's first
    character, moves `end` to the last accepted character, and reports `text`
    as whatever `as_data()` returns for the same node — including the
    indentation preserved past the baseline (Contract 03, D11) — so
    `str(node.as_source()) == node.as_data()` holds.
    """

    def test_it_should_preserve_past_baseline_indentation_in_the_reported_span(self) -> None:
        original = 'key:\n  first\n    indented\n  back'
        tree = parsers.parse(original, filename='doc.syml')

        data = tree.as_data()
        source = tree.as_source()['key']

        assert data == {'key': 'first\n  indented\nback'}
        assert source.text == 'first\n  indented\nback'
        assert str(source) == data['key']
        assert source.start == basetypes.Pos(index=7, line=2, column=2)
        assert source.end == basetypes.Pos(index=32, line=4, column=6)
