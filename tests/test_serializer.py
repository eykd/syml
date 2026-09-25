"""Tests for the `dumps`/`dump` type contract (Contract 07 §Type contract)."""

from __future__ import annotations

from enum import Enum

import pytest
from serialization_corpus import CORPUS, UNREPRESENTABLE

from syml import loads, serializer
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
            ('', '\n'),
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
            ('  hello', 'begins with whitespace'),
            ([' x\ny'], 'begins with whitespace'),
            ('x\n\ny', 'contains a blank or whitespace-only line'),
            ({'k': 'a\n   '}, 'contains a blank or whitespace-only line'),
            ({'k': 'x\n'}, 'contains a blank or whitespace-only line'),
            ({'k': 'a\n\tb'}, 'a line begins with a tab'),
            ({'k': 'a\n  \tb'}, 'a line begins with a tab'),
            ({'k': 'a\n# c'}, 'a line begins with a comment marker'),
            ('x\n  //c', 'a line begins with a comment marker'),
            ('# c', 'a line begins with a comment marker'),
            ({'k': 'a\n  - b'}, 'a line would lex as structure'),
            ({'k': 'a\nlisten: x'}, 'a line would lex as structure'),
            ('k:', 'a line would lex as structure'),
            ('- x', 'a line would lex as structure'),
            ('- ' * 200 + 'x', 'a line would lex as structure'),
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


class TestLexesAsStructure:
    """`_lexes_as_structure` re-reads one physical line with the real parser."""

    @pytest.mark.parametrize('line', ['- x', 'key: v', 'k:', '-', '- ' * 200 + 'x'])
    def test_it_should_report_structure(self, line: str) -> None:
        assert serializer._lexes_as_structure(line) is True  # noqa: SLF001

    @pytest.mark.parametrize('line', ['text', 'Listen: here', 'key:value', '-42', '#x', '//x'])
    def test_it_should_report_text_or_a_comment_as_not_structure(self, line: str) -> None:
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
            '#comment',  # begins with '#'
            '//comment',  # begins with '//'
            'a\rb',  # control character other than LF/TAB
            ' leading',  # leading whitespace on its first line
            'x\n\ny',  # contains a blank line
        ],
    )
    def test_it_should_raise_unrepresentable_value_error_for_a_root_scalar_with_no_encoding(self, value: str) -> None:
        with pytest.raises(UnrepresentableValueError):
            serializer.dumps(value)

    @pytest.mark.parametrize('value', ['hello', 'a\nb', 'trailing ', "''", '""', "'Tis", 'Listen: here'])
    def test_it_should_serialize_a_representable_root_scalar(self, value: str) -> None:
        assert loads(serializer.dumps(value)) == value


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
