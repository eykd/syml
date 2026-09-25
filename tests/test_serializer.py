"""Tests for the `dumps`/`dump` type contract (Contract 07 §Type contract)."""

from __future__ import annotations

from enum import Enum

import pytest
from serialization_corpus import CORPUS, UNREPRESENTABLE

from syml import loads, parsers, serializer
from syml.exceptions import UnrepresentableValueError


class TestDumpsLoadsRoundTripsOverCorpus:
    """The shared round-trip corpus (Contract 07, pass 25) round-trips through dumps/loads."""

    @pytest.mark.parametrize('corpus_id', sorted(CORPUS))
    def test_it_should_round_trip_every_corpus_entry_through_dumps_and_loads(self, corpus_id: str) -> None:
        value = CORPUS[corpus_id]
        assert loads(serializer.dumps(value)) == value


class TestDumpsRaisesForEveryUnrepresentableCorpusEntry:
    """Every `UNREPRESENTABLE` corpus entry makes `dumps` raise (§11.2.1-.3)."""

    @pytest.mark.parametrize('corpus_id', sorted(UNREPRESENTABLE))
    def test_it_should_raise_unrepresentable_value_error_for_every_unrepresentable_entry(self, corpus_id: str) -> None:
        with pytest.raises(UnrepresentableValueError):
            serializer.dumps(UNREPRESENTABLE[corpus_id])  # type: ignore[arg-type]


class TestDumpsStructureShapedStringsArePositionDependent:
    """A structure-shaped single-line string is fine as a mapping value but not as a list item.

    After `key: ` the rest of the line is always the value (§4.1), so the
    string is written inline and reads back literally. After `- ` the value
    position re-lexes as structure, so the same string has no encoding
    there.
    """

    @pytest.mark.parametrize(
        ('list_item_id', 'mapping_value_id'),
        [
            ('looks_like_key_value', 'looks_like_key_value_as_mapping_value'),
            ('looks_like_list_item', 'looks_like_list_item_as_mapping_value'),
            ('stranded_double_quote', 'stranded_double_quote_as_mapping_value'),
            ('stranded_single_quote', 'stranded_single_quote_as_mapping_value'),
            ('literal_backslash_u003a', 'literal_backslash_u003a_as_mapping_value'),
            ('mixed_quote_backslash', 'mixed_quote_backslash_as_mapping_value'),
            ('deep_dash_run_list_item', 'deep_dash_run_mapping_value'),
        ],
    )
    def test_it_should_round_trip_the_mapping_value_and_reject_the_list_item(
        self, list_item_id: str, mapping_value_id: str
    ) -> None:
        list_item_value = UNREPRESENTABLE[list_item_id]
        mapping_value = CORPUS[mapping_value_id]
        assert isinstance(list_item_value, list)
        assert isinstance(mapping_value, dict)
        assert list(mapping_value.values()) == list_item_value
        assert loads(serializer.dumps(mapping_value)) == mapping_value
        with pytest.raises(UnrepresentableValueError):
            serializer.dumps(list_item_value)


class TestDumpsLiteralValues:
    """D18: every string is written literally, with no quoting or escaping."""

    @pytest.mark.parametrize(
        ('value', 'expected'),
        [
            ({'k': '"q" t'}, 'k: "q" t\n'),
            (["'Tis"], "- 'Tis\n"),
            ({'k': "''"}, "k: ''\n"),
            ({'k': 'trail '}, 'k: trail \n'),
            ({'k': 'a\tb'}, 'k: a\tb\n'),
            ({'k': 'key: value'}, 'k: key: value\n'),
            ({'k': '- x'}, 'k: - x\n'),
            (['#x'], '- #x\n'),
            (['Listen: here'], '- Listen: here\n'),
            (['key:value'], '- key:value\n'),
            (['-42'], '- -42\n'),
        ],
    )
    def test_it_should_write_a_single_line_string_inline_and_unchanged(self, value: object, expected: str) -> None:
        assert serializer.dumps(value) == expected  # type: ignore[arg-type]
        assert loads(expected) == value

    @pytest.mark.parametrize(
        ('value', 'expected'),
        [
            ({'k': ''}, 'k:\n'),
            ([''], '-\n'),
            ('', ''),
        ],
    )
    def test_it_should_write_the_empty_string_as_the_positions_empty_convention(
        self, value: object, expected: str
    ) -> None:
        """Rule A: nothing after the marker; the empty root scalar is the empty document."""
        assert serializer.dumps(value) == expected  # type: ignore[arg-type]
        assert loads(expected) == value


class TestDumpsBlockForm:
    """A string containing a line feed, or any root scalar, is written in block form (§5.1, §5.3)."""

    @pytest.mark.parametrize(
        ('value', 'expected'),
        [
            ({'k': 'x\ny'}, 'k:\n  x\n  y\n'),
            (['x\ny'], '-\n  x\n  y\n'),
            ('x\ny', 'x\ny\n'),
            ('hello', 'hello\n'),
            ({'a': {'b': 'x\ny'}}, 'a:\n  b:\n    x\n    y\n'),
            (['a\nb', {'m': 'x\ny'}], '-\n  a\n  b\n- m:\n    x\n    y\n'),
        ],
    )
    def test_it_should_write_each_line_two_spaces_past_its_marker(self, value: object, expected: str) -> None:
        assert serializer.dumps(value) == expected  # type: ignore[arg-type]
        assert loads(expected) == value

    @pytest.mark.parametrize(
        ('value', 'expected'),
        [
            ({'k': 'a\n  b\nc'}, 'k:\n  a\n    b\n  c\n'),
            ({'a': {'b': 'x\n  y'}}, 'a:\n  b:\n    x\n      y\n'),
            ('hello\n  world\nagain', 'hello\n  world\nagain\n'),
        ],
    )
    def test_it_should_preserve_the_relative_indentation_of_later_lines(self, value: object, expected: str) -> None:
        assert serializer.dumps(value) == expected  # type: ignore[arg-type]
        assert loads(expected) == value

    @pytest.mark.parametrize('value', ['Listen: here', 'a\nListen: x', '\'Tis\n"q"'])
    def test_it_should_accept_block_lines_that_read_back_as_text(self, value: str) -> None:
        assert loads(serializer.dumps(value)) == value


class TestDumpsUnrepresentableScalars:
    """§11.2.1: one case per reason a string has no encoding at its position."""

    @pytest.mark.parametrize(
        ('value', 'reason'),
        [
            ({'k': 'a\rb'}, 'contains a control character'),
            ({'k': 'a\x00b'}, 'contains a control character'),
            ('a\x85b', 'contains a control character'),
            ({'k': ' lead'}, 'begins with whitespace'),
            ({'k': '\tlead'}, 'begins with whitespace'),
            ([' x\ny'], 'begins with whitespace'),
            ({'k': 'a\n   '}, 'contains a non-empty whitespace-only line'),
            ({'k': 'x\n'}, 'ends with a trailing newline'),
            ({'k': '\nx'}, 'begins with a blank line'),
            ('x\n', 'ends with a trailing newline'),
            ({'k': 'a\n\tb'}, 'a line begins with a tab'),
            ({'k': 'a\n  \tb'}, 'a line begins with a tab'),
            ('a\n# b', 'a line begins with a comment marker'),
            ('# c', 'a line begins with a comment marker'),
            ('k:', 'a line would lex as structure'),
            ('- x', 'a line would lex as structure'),
            ('- ' * 200 + 'x', 'a line would lex as structure'),
            ('  - b', 'a line would lex as structure'),
            (['- x'], 'a list item value would lex as structure'),
            (['key: v'], 'a list item value would lex as structure'),
            (['-'], 'a list item value would lex as structure'),
            (['- ' * 200 + 'x'], 'a list item value would lex as structure'),
        ],
    )
    def test_it_should_raise_with_the_reason_in_the_message(self, value: object, reason: str) -> None:
        with pytest.raises(UnrepresentableValueError) as excinfo:
            serializer.dumps(value)  # type: ignore[arg-type]
        assert reason in excinfo.value.args[0]

    @pytest.mark.parametrize(
        'value',
        [
            {'k': 'a\n  - b'},
            {'k': 'a\nlisten: x'},
            {'k': 'a\n# c'},
            'x\n  //c',
            '  hello',
            'x\n\ny',
            ' leading',
        ],
    )
    def test_it_should_round_trip_values_no_longer_refused(self, value: object) -> None:
        """D21/D22/D23/FR-005: a later line's shape, a mid-value blank line, and a root scalar's own leading spaces no longer make a value unrepresentable."""
        assert loads(serializer.dumps(value)) == value  # type: ignore[arg-type]


class TestLexesAsStructure:
    """`_lexes_as_structure` re-reads one physical line with the real parser."""

    @pytest.mark.parametrize('line', ['- x', 'key: v', 'k:', '-', '- ' * 200 + 'x'])
    def test_it_should_report_structure(self, line: str) -> None:
        assert serializer._lexes_as_structure(line) is True  # noqa: SLF001

    @pytest.mark.parametrize('line', ['text', 'Listen: here', 'key:value', '-42', '#x', '//x'])
    def test_it_should_report_text_or_a_comment_as_not_structure(self, line: str) -> None:
        assert serializer._lexes_as_structure(line) is False  # noqa: SLF001

    @pytest.mark.parametrize('line', ['﻿- x', '﻿key: v', '﻿k:', '﻿-'])
    def test_it_should_not_strip_a_leading_bom_before_judging_structure(self, line: str) -> None:
        """No §9.0 pre-processing runs on the isolated line (US3-5, FR-006): a leading U+FEFF is content."""
        assert serializer._lexes_as_structure(line) is False  # noqa: SLF001


class TestWithMarker:
    """`_with_marker` attaches a scalar's rendered lines to its `key:`/`-` marker."""

    def test_it_should_return_the_bare_marker_for_no_lines(self) -> None:
        assert serializer._with_marker('k:', []) == ['k:']  # noqa: SLF001

    def test_it_should_put_a_single_line_inline_after_one_space(self) -> None:
        assert serializer._with_marker('  k:', ['    v']) == ['  k: v']  # noqa: SLF001

    def test_it_should_put_multiple_lines_in_block_form_under_the_marker(self) -> None:
        assert serializer._with_marker('-', ['  a', '  b']) == ['-', '  a', '  b']  # noqa: SLF001


class TestKeyIsRepresentable:
    """`key_is_representable` (§11.2.3, §4.5, xreq.16): ASCII, lowercase, leading letter, or not a key."""

    @pytest.mark.parametrize('key', ['k', 'look-in-dark', 'first_name', 'k1', 'a-b-c'])
    def test_it_should_accept_a_representable_key(self, key: str) -> None:
        assert serializer.key_is_representable(key) is True

    @pytest.mark.parametrize(
        'key',
        [
            '',
            'a b',
            'a:b',
            '#c',
            '//c',
            'Name',
            'nAme',
            'a#b',
            '\u540d\u524d',
            '\u217b',
            '\u216b',
            '\ufeffk',
            '\u01c5',
            '\u00c9t\u00e9',
            'a\x01b',
            'a\tb',
        ],
    )
    def test_it_should_reject_an_unrepresentable_key(self, key: str) -> None:
        assert serializer.key_is_representable(key) is False


class TestDumpsRuleG:
    """Rule G: exactly one space separates `-` from an inline mapping's first key."""

    def test_it_should_put_one_space_between_the_marker_and_a_mapping_key(self) -> None:
        assert serializer.dumps([{'a': '1', 'b': '2'}]) == '- a: 1\n  b: 2\n'

    def test_it_should_attach_a_nested_mapping_under_a_list_item(self) -> None:
        assert serializer.dumps([{'a': {'b': 'c'}}]) == '- a:\n    b: c\n'


class TestDumpsResidualUnrepresentableSet:
    """Contract 04's residual nine-item set: exact output and the 32-marker recursion guard."""

    def test_it_should_write_a_paragraph_break_as_an_empty_physical_line(self) -> None:
        """US3-1: a blank line inside a value is one empty physical line, no indentation."""
        value = {'k': 'Para one.\n\nPara two.'}
        expected = 'k:\n  Para one.\n\n  Para two.\n'
        assert serializer.dumps(value) == expected
        assert loads(expected) == value

    def test_it_should_write_a_structure_shaped_later_line_unrestricted(self) -> None:
        """US3-2: a later block line free to lex as structure still round-trips as text."""
        value = {'k': 'some prose\n- used as a dash\nkey: v'}
        expected = 'k:\n  some prose\n  - used as a dash\n  key: v\n'
        assert serializer.dumps(value) == expected
        assert loads(expected) == value

    def test_it_should_write_an_indented_root_scalar_at_column_0(self) -> None:
        """US3-3: FR-005 — a root scalar's own leading spaces are literal, unstripped."""
        value = '  hello\nworld'
        expected = '  hello\nworld\n'
        assert serializer.dumps(value) == expected
        assert loads(expected) == value

    @pytest.mark.parametrize(
        'value',
        [
            {'k': 'a\n' + '- ' * 32 + 'x'},
            ['a\n' + '- ' * 32 + 'x'],
            'a\n' + '- ' * 32 + 'x',
        ],
    )
    def test_it_should_accept_a_later_line_with_32_markers(self, value: object) -> None:
        assert loads(serializer.dumps(value)) == value  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        'value',
        [
            {'k': 'a\n' + '- ' * 33 + 'x'},
            ['a\n' + '- ' * 33 + 'x'],
            'a\n' + '- ' * 33 + 'x',
        ],
    )
    def test_it_should_refuse_a_later_line_with_33_markers(self, value: object) -> None:
        with pytest.raises(UnrepresentableValueError):
            serializer.dumps(value)  # type: ignore[arg-type]

    def test_it_should_refuse_33_tab_separated_markers(self) -> None:
        """Tabs separate markers too, not only spaces."""
        with pytest.raises(UnrepresentableValueError):
            serializer.dumps({'k': 'a\n' + '-\t' * 33 + 'x'})

    def test_it_should_count_a_trailing_bare_dash_as_a_marker(self) -> None:
        """33 markers with the last one bare (no trailing space) still refuses."""
        with pytest.raises(UnrepresentableValueError):
            serializer.dumps({'k': 'a\n  ' + '- ' * 32 + '-'})

    def test_it_should_not_count_a_dash_before_non_whitespace_as_a_marker(self) -> None:
        """syml-cjk2.9: `-42` is text (§7.6), not a 33rd marker, so 32 markers round-trip."""
        value = {'k': 'a\n' + '- ' * 32 + '-42'}
        assert loads(serializer.dumps(value)) == value

    def test_it_should_round_trip_a_long_chain_after_an_inline_key(self) -> None:
        """A chain after `k: ` is inline `data`, not a later block line, so it never recurses."""
        value = {'k': 'a\nk: ' + '- ' * 100 + 'x'}
        assert loads(serializer.dumps(value)) == value

    def test_it_should_round_trip_a_short_later_line_chain(self) -> None:
        value = {'k': 'a\n' + '- ' * 20 + 'x'}
        assert loads(serializer.dumps(value)) == value

    def test_it_should_refuse_a_deep_later_line_load_only_family(self) -> None:
        """L3: `loads` can read a 40-marker chain at a shallow stack; `dumps` refuses it at every stack."""
        value = loads('k:\n  a\n  ' + '- ' * 40 + 'x')
        with pytest.raises(UnrepresentableValueError):
            serializer.dumps(value)

    def _dumps_after_burning_frames(self, value: object, depth: int) -> str | None:
        """Recurse `depth` frames deep before calling dumps, to prove the bound is a fixed count."""
        if depth <= 0:
            try:
                serializer.dumps(value)  # type: ignore[arg-type]
            except UnrepresentableValueError:
                return 'refused'
            return 'accepted'
        return self._dumps_after_burning_frames(value, depth - 1)

    def test_it_should_refuse_33_markers_the_same_way_at_a_shallow_or_deep_stack(self) -> None:
        value = {'k': 'a\n' + '- ' * 33 + 'x'}
        assert self._dumps_after_burning_frames(value, 0) == 'refused'
        assert self._dumps_after_burning_frames(value, 500) == 'refused'


class TestDumpsUnrepresentableEmptyContainers:
    """§11.2.2 — empty list/mapping raise UnrepresentableValueError at any depth (D1)."""

    @pytest.mark.parametrize(
        'value',
        [
            [],
            {},
            {'a': []},
            {'a': {'b': {}}},
        ],
    )
    def test_it_should_raise_unrepresentable_value_error_for_an_empty_container_at_any_depth(
        self, value: object
    ) -> None:
        with pytest.raises(UnrepresentableValueError):
            serializer.dumps(value)  # type: ignore[arg-type]


class TestDumpsTypeContract:
    def test_it_should_serialize_str_list_and_dict_recursively(self) -> None:
        assert serializer.dumps({'a': ['b', {'c': 'd'}]}) == 'a:\n  - b\n  - c: d\n'

    @pytest.mark.parametrize('value', [1, 1.5, True, None, object()])
    def test_it_should_raise_type_error_for_non_syml_types(self, value: object) -> None:
        with pytest.raises(TypeError):
            serializer.dumps(value)  # type: ignore[arg-type]

    @pytest.mark.parametrize('key', [1, None, b'k'])
    def test_it_should_raise_type_error_for_non_str_mapping_keys(self, key: object) -> None:
        with pytest.raises(TypeError):
            serializer.dumps({key: 'v'})  # type: ignore[dict-item]


class TestDumpsAcceptsSource:
    """A `Source` is accepted anywhere a `str` key or scalar is (FR-014, US3-8).

    `as_source()` reads keys and scalars as their `.text` before any type
    check, so `dumps(parse(t).as_source())` round-trips like
    `dumps(parse(t).as_data())`.
    """

    def test_it_should_round_trip_a_source_mapping_key_and_scalar_value(self) -> None:
        text = 'k: v\n'
        source = parsers.parse(text).as_source()
        assert serializer.dumps(source) == text == serializer.dumps(loads(text))

    def test_it_should_round_trip_a_source_list_item(self) -> None:
        text = '- a\n- b\n'
        source = parsers.parse(text).as_source()
        assert serializer.dumps(source) == text

    def test_it_should_round_trip_a_root_source_scalar(self) -> None:
        text = 'hello\n'
        source = parsers.parse(text).as_source()
        assert serializer.dumps(source) == text


class TestDumpsUnrepresentableKeys:
    """§11.2.3 — keys with no encoding raise UnrepresentableValueError (D1, M8)."""

    @pytest.mark.parametrize(
        'key',
        [
            '',
            'a b',
            'a:b',
            '#comment',
            '//comment',
            'Name',
            '\u01c5',
        ],
    )
    def test_it_should_raise_unrepresentable_value_error_for_a_key_with_no_encoding(self, key: str) -> None:
        with pytest.raises(UnrepresentableValueError):
            serializer.dumps({key: 'v'})


class TestDumpsUnrepresentableRootScalars:
    """§11.2.1 — root scalars with no encoding raise UnrepresentableValueError (D17)."""

    @pytest.mark.parametrize(
        'value',
        [
            '- x',  # would lex as list_item
            'k: v',  # would lex as key_value
            '#comment',  # begins with '#' at column 0
            '//comment',  # begins with '//' at column 0
            'a\rb',  # control character other than LF/TAB
            '\tleading',  # leading tab on its first line
            'a\n# b',  # a later line begins with '#' at column 0 (item 9, root only)
            'a\n// b',  # a later line begins with '//' at column 0 (item 9, root only)
        ],
    )
    def test_it_should_raise_unrepresentable_value_error_for_a_root_scalar_with_no_encoding(self, value: str) -> None:
        with pytest.raises(UnrepresentableValueError):
            serializer.dumps(value)

    @pytest.mark.parametrize(
        'value',
        [
            'hello',
            'a\nb',
            'trailing ',
            "''",
            '""',
            "'Tis",
            'Listen: here',
            '  hello',  # FR-005: leading spaces on a root scalar's first line are literal
            '  hello\nworld',  # US3-3
            'x\n\ny',  # D22: a mid-value blank line is a paragraph break
            '  # x',  # D23: indented, so not a column-0 comment
            'a\n  # b',  # D23: indented later line, not a column-0 comment
        ],
    )
    def test_it_should_serialize_a_representable_root_scalar(self, value: str) -> None:
        assert loads(serializer.dumps(value)) == value


class TestDumpsErrorDataPath:
    """D30: `dumps` errors name the offending value's data path.

    `UnrepresentableValueError.path` and both errors' `str(e)` carry the
    path in Python subscript form (e.g. `['a']['b'][1]`); a root value's
    message has no path clause.
    """

    def test_it_should_have_no_path_clause_for_a_root_unrepresentable_scalar(self) -> None:
        with pytest.raises(UnrepresentableValueError) as excinfo:
            serializer.dumps('# comment')
        assert excinfo.value.path == ()
        assert ' at ' not in str(excinfo.value)

    def test_it_should_path_a_mapping_valued_unrepresentable_scalar_by_its_key(self) -> None:
        with pytest.raises(UnrepresentableValueError) as excinfo:
            serializer.dumps({'k': '\tlead'})
        assert excinfo.value.path == ('k',)
        assert str(excinfo.value).endswith(" at ['k']")

    def test_it_should_path_a_list_item_unrepresentable_scalar_by_its_index(self) -> None:
        with pytest.raises(UnrepresentableValueError) as excinfo:
            serializer.dumps(['- x'])
        assert excinfo.value.path == (0,)
        assert str(excinfo.value).endswith(' at [0]')

    def test_it_should_path_a_deeply_nested_unrepresentable_scalar(self) -> None:
        with pytest.raises(UnrepresentableValueError) as excinfo:
            serializer.dumps({'a': {'b': ['x', '\tlead']}})
        assert excinfo.value.path == ('a', 'b', 1)
        assert str(excinfo.value).endswith(" at ['a']['b'][1]")

    def test_it_should_path_an_empty_container_by_its_key(self) -> None:
        with pytest.raises(UnrepresentableValueError) as excinfo:
            serializer.dumps({'a': {}})
        assert excinfo.value.path == ('a',)

    def test_it_should_have_no_path_clause_for_a_root_type_error(self) -> None:
        with pytest.raises(TypeError) as excinfo:
            serializer.dumps(1)  # type: ignore[arg-type]
        assert not hasattr(excinfo.value, 'path')
        assert len(excinfo.value.args) == 1
        assert ' at ' not in str(excinfo.value)

    def test_it_should_path_a_deeply_nested_type_error(self) -> None:
        with pytest.raises(TypeError) as excinfo:
            serializer.dumps({'a': {'b': ['x', 1]}})
        assert not hasattr(excinfo.value, 'path')
        assert len(excinfo.value.args) == 1
        assert str(excinfo.value).endswith(" at ['a']['b'][1]")

    def test_it_should_not_render_a_tuple_repr_for_the_nested_type_error(self) -> None:
        with pytest.raises(TypeError) as excinfo:
            serializer.dumps({'a': {'b': ['x', 1]}})
        assert str(excinfo.value) != str((f'{1!r} is not representable in SYML (not str, list, or dict)', 1))

    def test_it_should_path_a_non_str_key_type_error_by_its_parent_mapping(self) -> None:
        with pytest.raises(TypeError) as excinfo:
            serializer.dumps({'a': {1: 'v'}})
        assert str(excinfo.value).endswith(" at ['a']")

    def test_it_should_path_an_unrepresentable_key_by_its_parent_mapping(self) -> None:
        with pytest.raises(UnrepresentableValueError) as excinfo:
            serializer.dumps({'a': {'Name': 'v'}})
        assert excinfo.value.path == ('a',)
        assert str(excinfo.value).endswith(" at ['a']")


class TestDumpsErrorDataPathIsBounded:
    """D30 (syml-cjk2.18): a hostile key or deep path still yields a bounded `str(e)`.

    `.path` (on `UnrepresentableValueError`) stays the full, untruncated
    tuple; only the rendered message clause is bounded.
    """

    def test_it_should_bound_a_hostile_key_in_a_type_error(self) -> None:
        huge_key = 'k' * 2_000_000
        with pytest.raises(TypeError) as excinfo:
            serializer.dumps({huge_key: 1})
        assert len(str(excinfo.value)) < 300

    def test_it_should_bound_a_hostile_key_in_an_unrepresentable_value_error(self) -> None:
        huge_key = 'k' * 2_000_000
        with pytest.raises(UnrepresentableValueError) as excinfo:
            serializer.dumps({huge_key: {'b': '\x00'}})
        assert len(str(excinfo.value)) < 300
        assert excinfo.value.path == (huge_key, 'b')

    def test_it_should_bound_a_hostile_unrepresentable_mapping_key_itself(self) -> None:
        """syml-cjk2.25: the §11.2.3 unrepresentable-key message, not only the path."""
        huge_key = 'K' * 2_000_000
        with pytest.raises(UnrepresentableValueError) as excinfo:
            serializer.dumps({huge_key: 'x'})
        message = str(excinfo.value)
        assert len(message) < 300
        assert message.startswith("'" + 'K' * 80 + '…')

    def test_it_should_bound_a_hostile_non_str_key_repr_in_a_type_error(self) -> None:
        """syml-cjk2.25: a non-str key's repr is windowed, not printed whole."""
        huge_key = ('t',) * 300_000
        with pytest.raises(TypeError) as excinfo:
            serializer.dumps({huge_key: 'x'})  # type: ignore[dict-item]
        message = str(excinfo.value)
        assert len(message) < 300
        assert message.startswith("('t', 't', 't',")

    def test_it_should_bound_a_hostile_value_repr_in_a_not_representable_type_error(self) -> None:
        """syml-cjk2.25: the offending value's repr in `_not_representable` is windowed."""
        with pytest.raises(TypeError) as excinfo:
            serializer.dumps({'a': ('t',) * 300_000})
        message = str(excinfo.value)
        assert len(message) < 300
        assert message.startswith("('t', 't', 't',")

    def test_it_should_bound_a_hostile_value_repr_in_an_unrepresentable_value_error(self) -> None:
        """syml-cjk2.25: the offending scalar's repr in `_unrepresentable` is windowed."""
        huge_value = 'y' * 2_000_000 + '\x00'
        with pytest.raises(UnrepresentableValueError) as excinfo:
            serializer.dumps({'a': huge_value})
        message = str(excinfo.value)
        assert len(message) < 300
        assert message.startswith("'" + 'y' * 80 + '…')


class TestDumpsLeadingFeffProtectiveDoubling:
    """A leading U+FEFF gets one extra U+FEFF prepended, since loads strips one (§9.0)."""

    def test_it_should_double_a_leading_feff_on_a_root_scalar(self) -> None:
        assert serializer.dumps('\ufeffhello') == '\ufeff\ufeffhello\n'


class _Mood(str, Enum):  # noqa: UP042 -- StrEnum.__str__ returns the value, which would skip the str.__str__ path under test
    """A (str, Enum) whose members serialize as their string value."""

    CALM = 'calm'


class TestDumpsStrSubclass:
    """A str subclass is written as its string value, never its repr."""

    def test_it_should_write_a_str_enum_member_as_its_value_at_every_position(self) -> None:
        assert serializer.dumps({'mood': _Mood.CALM, 'list': [_Mood.CALM]}) == 'mood: calm\nlist:\n  - calm\n'
        assert serializer.dumps(_Mood.CALM) == 'calm\n'

    def test_it_should_write_a_str_enum_member_as_a_key_by_its_value(self) -> None:
        assert serializer.dumps({_Mood.CALM: 'v'}) == 'calm: v\n'


class _RecordingTextFile:
    """A minimal `IO[str]`-shaped stub that records every `write()` call."""

    def __init__(self) -> None:
        """Initialize with an empty call log."""
        self.write_calls: list[str] = []

    def write(self, s: str) -> int:
        """Record the written string and return its length, like a real file."""
        self.write_calls.append(s)
        return len(s)


class TestDumpSingleWriteSemantics:
    """dump() calls file_obj.write() exactly once, with the whole dumps() result (Contract 07)."""

    def test_it_should_write_the_whole_serialized_result_in_a_single_write_call(self) -> None:
        file_obj = _RecordingTextFile()
        serializer.dump({'a': '1', 'b': '2'}, file_obj)  # type: ignore[arg-type]
        assert file_obj.write_calls == [serializer.dumps({'a': '1', 'b': '2'})]
