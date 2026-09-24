"""Tests for the `dumps`/`dump` type contract (Contract 07 §Type contract)."""

from __future__ import annotations

import pytest

from syml import serializer
from syml.exceptions import UnrepresentableValueError


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
