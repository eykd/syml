"""Tests for the `dumps`/`dump` type contract (Contract 07 §Type contract)."""

from __future__ import annotations

import pytest
from serialization_corpus import CORPUS

from syml import loads, serializer
from syml.exceptions import UnrepresentableValueError

_PENDING_CORPUS_ROUND_TRIP_IDS: frozenset[str] = frozenset()


class TestDumpsLoadsRoundTripsOverCorpus:
    """The shared round-trip corpus (Contract 07, pass 25) round-trips through dumps/loads."""

    @pytest.mark.parametrize(
        'corpus_id',
        [
            pytest.param(
                corpus_id,
                marks=pytest.mark.xfail(
                    strict=True,
                    reason='pending syml-x0m.5.8.25 corpus chain - remove when this entry passes',
                ),
            )
            if corpus_id in _PENDING_CORPUS_ROUND_TRIP_IDS
            else corpus_id
            for corpus_id in sorted(CORPUS)
        ],
    )
    def test_it_should_round_trip_every_corpus_entry_through_dumps_and_loads(self, corpus_id: str) -> None:
        value = CORPUS[corpus_id]
        assert loads(serializer.dumps(value)) == value


class TestDumpsLoadsRoundTripsKeyValueShapedStringsAtBothPositions:
    """Every key:value-shaped corpus string round-trips both as a mapping value and as a list item."""

    @pytest.mark.parametrize(
        ('list_item_id', 'mapping_value_id'),
        [
            ('looks_like_key_value', 'looks_like_key_value_as_mapping_value'),
            ('looks_like_key_value_no_space', 'looks_like_key_value_no_space_as_mapping_value'),
            ('stranded_double_quote', 'stranded_double_quote_as_mapping_value'),
            ('stranded_single_quote', 'stranded_single_quote_as_mapping_value'),
            ('colon_escape_list_item', 'colon_escape_list_item_as_mapping_value'),
            ('literal_backslash_u003a', 'literal_backslash_u003a_as_mapping_value'),
            ('mixed_quote_backslash', 'mixed_quote_backslash_as_mapping_value'),
        ],
    )
    def test_it_should_round_trip_the_same_key_value_shaped_string_as_a_mapping_value(
        self, list_item_id: str, mapping_value_id: str
    ) -> None:
        assert list_item_id in CORPUS, f'{list_item_id} missing from CORPUS'
        assert mapping_value_id in CORPUS, f'{mapping_value_id} missing from CORPUS'
        list_item_value = CORPUS[list_item_id]
        mapping_value = CORPUS[mapping_value_id]
        assert isinstance(list_item_value, list)
        assert isinstance(mapping_value, dict)
        assert list(mapping_value.values()) == list_item_value
        assert loads(serializer.dumps(mapping_value)) == mapping_value


class TestDumpsQuotingTable:
    """§11.2.1 quoting table rules A-G, including the list-item re-lex rule."""

    def test_it_should_double_quote_and_escape_colon_for_a_list_item_that_would_relex_as_a_mapping(
        self,
    ) -> None:
        # Rule D: 'a: b' at a list-item position would match key_value, so it
        # must be quoted. Both the single- and plain-double-quoted renderings
        # re-lex as a mapping (per the re-lex rule), so the emitted form must
        # be double-quoted with the ':' escaped as \u003a.
        assert serializer.dumps(['a: b']) == '- "a\\u003a b"\n'

    def test_it_should_single_quote_a_list_item_that_stays_literal_after_quoting(
        self,
    ) -> None:
        # Rule D: 'k:' at a list-item position would match key_value, so it
        # must be quoted. Unlike 'a: b', the single-quoted rendering does not
        # re-lex as a mapping (it falls back to a literal `data` value), so
        # the single-quoted form is kept, per the re-lex rule's table.
        assert serializer.dumps(['k:']) == "- 'k:'\n"

    def test_it_should_treat_a_deeply_nested_list_item_string_as_matching_structure(
        self,
    ) -> None:
        # Rule D's probe treats a RecursionError from the `structure` grammar
        # as "matches" (plan.md pass 4): only a `- `-led string recurses this
        # deep, so it must be quoted like any other list-item value.
        value = '- ' * 150 + 'x'
        assert serializer.dumps([value]) == "- '" + value + "'\n"

    def test_it_should_round_trip_a_mapping_value_with_leading_and_trailing_space(
        self,
    ) -> None:
        # §11.2.1's quoting table is only wired up for list items so far
        # (syml-x0m.5.8.5-.7); a mapping value with leading/trailing
        # whitespace is written raw (`_render_mapping_lines` does not quote),
        # so `loads` strips the padding on read-back and the round trip
        # fails.
        value = {'k': ' x '}
        assert loads(serializer.dumps(value)) == value

    def test_it_should_not_raise_parse_error_for_a_value_whose_single_quote_relex_fails(
        self,
    ) -> None:
        # `_relexes_as_literal` calls the `line` grammar rule without
        # catching parsimonious.exceptions.ParseError, so a candidate whose
        # single-quoted rendering fails to re-lex crashes `dumps` instead of
        # falling back to the escaped double-quoted form.
        serializer.dumps(["k: 'v' x"])

    def test_it_should_round_trip_a_mapping_value_that_is_the_empty_string(
        self,
    ) -> None:
        # Rule A: the empty string is written via the position's empty-value
        # convention (nothing after `key:`), never `''` or `""`, so a mapping
        # value that is already empty needs no quoting.
        value = {'k': ''}
        assert loads(serializer.dumps(value)) == value


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
        ],
    )
    def test_it_should_raise_unrepresentable_value_error_for_a_key_with_no_encoding(self, key: str) -> None:
        with pytest.raises(UnrepresentableValueError):
            serializer.dumps({key: 'v'})


class TestDumpsUnrepresentableRootScalars:
    """§11.2.4 — root scalars with no encoding raise UnrepresentableValueError (D17)."""

    @pytest.mark.parametrize(
        'value',
        [
            '- x',  # (a) would lex as list_item on some line
            'k: v',  # (a) would lex as key_value on some line
            '#comment',  # (b) begins with '#'
            '//comment',  # (b) begins with '//'
            'a\nb',  # (c) contains a control character (\n)
            ' leading',  # (d) leading whitespace
            'trailing ',  # (d) trailing whitespace
            "''",  # (e) exactly two single quotes
            '""',  # (e) exactly two double quotes
        ],
    )
    def test_it_should_raise_unrepresentable_value_error_for_a_root_scalar_with_no_encoding(self, value: str) -> None:
        with pytest.raises(UnrepresentableValueError):
            serializer.dumps(value)

    def test_it_should_serialize_a_representable_root_scalar(self) -> None:
        assert serializer.dumps('hello') == 'hello\n'


class TestDumpsLeadingFeffProtectiveDoubling:
    """A leading U+FEFF gets one extra U+FEFF prepended, since loads strips one (§9.0)."""

    def test_it_should_double_a_leading_feff_on_a_root_scalar(self) -> None:
        assert serializer.dumps('\ufeffhello') == '\ufeff\ufeffhello\n'


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
