"""Tests for the `dumps`/`dump` type contract (Contract 07 §Type contract)."""

from __future__ import annotations

import pytest

from syml import serializer


class TestDumpsQuotingTable:
    """§11.2.1 quoting table rules A-G, including the list-item re-lex rule."""

    def test_it_should_double_quote_and_escape_colon_for_a_list_item_that_would_relex_as_a_mapping(
        self,
    ) -> None:
        # Rule D: 'a: b' at a list-item position would match key_value, so it
        # must be quoted. Both the single- and plain-double-quoted renderings
        # re-lex as a mapping (per the re-lex rule), so the emitted form must
        # be double-quoted with the ':' escaped as :.
        assert serializer.dumps(['a: b']) == '- "a\\u003a b"\n'


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
