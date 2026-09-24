"""Shared round-trip corpus for `dumps`/`loads` (Contract 07, pass 25).

Not a test module (does not start with `test_`, so pytest never collects
it), but it is inside the mypy file set. `tests/test_serializer.py` and
US7's acceptance binding both import from here, so an entry is exercised by
both the unit suite and `just acceptance`, and a stale `Examples:` corpus id
in the feature file fails with `KeyError` rather than silently passing.

`CORPUS` holds identifier -> a representable `SymlInput` value: `dumps(v)`
must succeed and `loads(dumps(v)) == v` must hold. `UNREPRESENTABLE` holds
identifier -> a `SymlInput` value for which `dumps` must raise
`UnrepresentableValueError`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: nocover
    from syml.basetypes import SymlInput

CORPUS: dict[str, SymlInput] = {
    'empty_string': '',
    'leading_trailing_space': {'k': ' x '},
    'leading_trailing_tab': {'k': '\tx\t'},
    'contains_newline': {'k': 'a\nb'},
    'contains_cr': {'k': 'a\rb'},
    'contains_nul': {'k': 'a\x00b'},
    'looks_like_key_value': ['key: value'],
    'looks_like_key_value_as_mapping_value': {'k': 'key: value'},
    'looks_like_key_value_no_space': ['key:value'],
    'looks_like_key_value_no_space_as_mapping_value': {'k': 'key:value'},
    'looks_like_list_item': ['- x'],
    'looks_like_negative_number': ['-42'],
    'starts_with_single_quote': ["'x"],
    'starts_with_double_quote': ['"x'],
    'starts_with_hash': ['#x'],
    'starts_with_slashslash': ['//x'],
    'literal_single_quotes': {'k': "''"},
    'literal_double_quotes': {'k': '""'},
    'colon_escape_list_item': ['a\\: b'],
    'colon_escape_list_item_as_mapping_value': {'k': 'a\\: b'},
    'literal_backslash_u003a': ['a: \\u003a'],
    'literal_backslash_u003a_as_mapping_value': {'k': 'a: \\u003a'},
    'mixed_quote_backslash': ['a: \'b" \\c'],
    'mixed_quote_backslash_as_mapping_value': {'k': 'a: \'b" \\c'},
    'stranded_double_quote': ['k: "a" x'],
    'stranded_double_quote_as_mapping_value': {'k': 'k: "a" x'},
    'stranded_single_quote': ["k: 'v' x"],
    'stranded_single_quote_as_mapping_value': {'k': "k: 'v' x"},
    'deep_dash_run_list_item': ['- ' * 200 + 'x'],
    'deep_dash_run_mapping_value': {'k': '- ' * 200 + 'x'},
    'astral_plane_char': {'k': '\U0001d54a'},
    'combining_char': {'k': 'é'},
    'nested_depth_4': {'a': {'b': {'c': {'d': 'e'}}}},
    'list_of_mappings': [{'a': '1'}, {'b': '2'}],
    'insertion_order_mapping': {'z': '1', 'a': '2', 'm': '3'},
    'leading_feff_root_scalar': '﻿hello',
    'leading_feff_first_key': {'﻿k': 'v'},
}

UNREPRESENTABLE: dict[str, object] = {
    'control_x01_key': {'a\x01b': 'v'},
    'control_x7f_key': {'a\x7fb': 'v'},
    'control_x9f_key': {'a\x9fb': 'v'},
    'control_x1c_key': {'a\x1cb': 'v'},
    'nbsp_key': {'a\xa0b': 'v'},
    'line_separator_key': {'a b': 'v'},  # noqa: RUF001 -- U+2028 is the point of this case
    'deep_dash_run_root_scalar': '- ' * 200 + 'x',
}
