"""Bindings for specs/acceptance-specs/US07-serialization.feature."""

from __future__ import annotations

import io
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from serialization_corpus import CORPUS, UNREPRESENTABLE

import syml
import syml.exceptions
from syml import serializer
from syml.exceptions import UnrepresentableValueError

pytestmark = pytest.mark.acceptance

scenarios('US07-serialization.feature')


@given(parsers.parse('the representable corpus value "{corpus_id}"'))
def given_corpus_value(context: dict[str, Any], corpus_id: str) -> None:
    """Store the named corpus value."""
    context['value'] = CORPUS[corpus_id]


@when('it is serialized with dumps and re-read with loads')
def when_serialized_and_reread(context: dict[str, Any]) -> None:
    """Round-trip the stored value through dumps and loads."""
    context['result'] = syml.loads(serializer.dumps(context['value']))


@then('the result equals the original value')
def then_result_equals_original(context: dict[str, Any]) -> None:
    """Assert the round-tripped result equals the original value."""
    assert context['result'] == context['value']


@given(parsers.parse('the unrepresentable corpus value "{corpus_id}"'))
def given_unrepresentable_corpus_value(context: dict[str, Any], corpus_id: str) -> None:
    """Store the named unrepresentable corpus value."""
    context['value'] = UNREPRESENTABLE[corpus_id]


@given('a mapping value containing a line feed')
def given_mapping_value_with_line_feed(context: dict[str, Any]) -> None:
    """Store a mapping whose value spans two lines."""
    context['value'] = {'k': 'a\nb'}


@given('a list item whose value is a mapping')
def given_list_item_holding_mapping(context: dict[str, Any]) -> None:
    """Store a list containing one mapping item."""
    context['value'] = [{'a': '1'}]


@given('a mapping with keys in a specific insertion order')
def given_mapping_with_insertion_order(context: dict[str, Any]) -> None:
    """Store a mapping whose keys are not in sorted order."""
    context['value'] = {'z': '1', 'a': '2', 'm': '3'}


@given('a structure containing an empty list or an empty mapping at any depth')
def given_structure_with_empty_container(context: dict[str, Any]) -> None:
    """Store a mapping whose value is an empty list."""
    context['value'] = {'a': []}


@given(
    parsers.parse(
        'a key containing whitespace, a colon, or an uppercase letter, the empty-string key, '
        'or a key beginning with "{marker}" or "{marker2}"'
    )
)
def given_unrepresentable_key(context: dict[str, Any], marker: str, marker2: str) -> None:
    """Store a mapping whose key contains whitespace, which has no SYML key encoding."""
    context['value'] = {'a b': 'v'}


@given(
    'a root scalar that would lex as structure, holds a control character other than tab, '
    'begins with a tab on its first line, or has a line beginning with a comment marker'
)
def given_unrepresentable_root_scalar(context: dict[str, Any]) -> None:
    """Store a root scalar that would lex as list structure."""
    context['value'] = '- x'


@when('it is serialized')
def when_serialized(context: dict[str, Any]) -> None:
    """Serialize the stored value, capturing dumps output or a raised error."""
    try:
        context['dumped'] = serializer.dumps(context['value'])
    except UnrepresentableValueError as exc:
        context['error'] = exc


@then(
    'the key stands alone on its line, each line of the value follows indented two spaces deeper, '
    'and loads reads the output back identically'
)
def then_written_in_block_form(context: dict[str, Any]) -> None:
    """Assert the value is in block form under its bare key and round-trips."""
    assert context['dumped'] == 'k:\n  a\n  b\n'
    assert syml.loads(context['dumped']) == context['value']


@then('exactly one space separates the marker from the key')
def then_one_space_separates_marker_from_key(context: dict[str, Any]) -> None:
    """Assert the list marker is followed by exactly one space before the key."""
    dumped = context['dumped']
    first_line = dumped.split('\n', 1)[0]
    assert first_line.startswith('- ')
    assert not first_line.startswith('-  ')


@then('its keys appear in that same order in the output')
def then_keys_in_insertion_order(context: dict[str, Any]) -> None:
    """Assert the dumped mapping's keys appear in the original insertion order."""
    dumped = context['dumped']
    value = context['value']
    positions = [dumped.index(f'{key}:') for key in value]
    assert positions == sorted(positions)


@then(parsers.parse('serializing fails with "{error_name}"'))
def then_serializing_fails(context: dict[str, Any], error_name: str) -> None:
    """Assert the captured error is an instance of the named exception class."""
    error_class = getattr(syml.exceptions, error_name)
    assert isinstance(context['error'], error_class)


@given('a value written to an open file handle with dump')
def given_value_written_with_dump(context: dict[str, Any]) -> None:
    """Write a representable value to an in-memory file handle with dump."""
    value = {'k': 'v'}
    file_obj = io.StringIO()
    serializer.dump(value, file_obj)
    file_obj.seek(0)
    context['value'] = value
    context['file_obj'] = file_obj


@when('that file is read back with load')
def when_file_read_back_with_load(context: dict[str, Any]) -> None:
    """Read the file handle back with syml.load."""
    context['result'] = syml.load(context['file_obj'], filename='<memory>')
