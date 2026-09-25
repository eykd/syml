"""Bindings for specs/acceptance-specs/US12-serializer-round-trip.feature."""

import ast
import re
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

import syml
import syml.exceptions as exc

pytestmark = pytest.mark.acceptance

scenarios('US12-serializer-round-trip.feature')

# Scenario Outline table cells come through pytest-bdd's gherkin parser with
# every literal backslash doubled (`Cell.from_dict`'s `_to_raw_string`), on
# top of the feature file's own "\\n"/"\\xNN"/"\\uNNNN" escape spelling; each
# pattern below matches a run of one-or-more backslashes so it decodes the
# same whether the text came from plain step text (single backslash) or a
# table cell (doubled backslash).
_ESCAPES = (
    (re.compile(r'\\+u([0-9a-fA-F]{4})'), lambda m: chr(int(m.group(1), 16))),
    (re.compile(r'\\+x([0-9a-fA-F]{2})'), lambda m: chr(int(m.group(1), 16))),
    (re.compile(r'\\+n'), '\n'),
)

#: Undoes the table-cell backslash doubling in front of an `n`/`x`/`u` escape
#: introducer, collapsing any run of backslashes down to exactly one so
#: `ast.literal_eval` interprets it as its own native `\n`/`\xNN`/`\uNNNN`
#: escape, whether the run came doubled from an Examples table or single
#: from plain step text.
_ESCAPE_INTRODUCER = re.compile(r'\\+(?=[nxu])')


def _decode(raw: str) -> str:
    r"""Decode the feature file's backslash-escaped "\\n"/"\\xNN"/"\\uNNNN" markers."""
    text = raw
    for pattern, replacement in _ESCAPES:
        text = pattern.sub(replacement, text)
    return text


@given(parsers.parse('the value {value}'))
def given_value(context: dict[str, Any], value: str) -> None:
    r"""Store the Python literal value described by `value` (a str, list, or dict).

    Gherkin's own Examples-table cell escaping already turns a table cell's
    "\\n" into a real newline character before pytest-bdd ever sees it
    (unlike "\\xNN"/"\\uNNNN", which are not standard table escapes and
    arrive with their backslash doubled instead) — so a literal newline is
    re-escaped here before `ast.literal_eval`, which cannot parse a raw
    newline inside a quoted string.
    """
    text = value.replace('\n', '\\n')
    context['value'] = ast.literal_eval(_ESCAPE_INTRODUCER.sub('\\\\', text))


@given(parsers.re(r'the scalar "(?P<text>[\s\S]*)"'))
def given_scalar(context: dict[str, Any], text: str) -> None:
    """Store the decoded scalar string."""
    context['value'] = _decode(text)


@given(parsers.parse('the parsed source of "{text}"'))
def given_parsed_source(context: dict[str, Any], text: str) -> None:
    """Store the `as_source()` result of parsing `text` (Source keys/scalars, FR-014)."""
    context['value'] = syml.parse(_decode(text)).as_source()


@given('the empty string')
def given_empty_string(context: dict[str, Any]) -> None:
    """Store the empty string."""
    context['value'] = ''


@when('it is dumped')
def when_dumped(context: dict[str, Any]) -> None:
    """Dump the stored value, capturing the output or a raised UnrepresentableValueError."""
    try:
        context['dumped'] = syml.dumps(context['value'])
    except exc.UnrepresentableValueError as error:
        context['error'] = error


@when('it is dumped and loaded again')
def when_dumped_and_loaded(context: dict[str, Any]) -> None:
    """Dump the stored value, then reload the output."""
    context['dumped'] = syml.dumps(context['value'])
    context['result'] = syml.loads(context['dumped'])


@then('the value round-trips unchanged')
def then_round_trips_unchanged(context: dict[str, Any]) -> None:
    """Assert the reloaded value equals the original."""
    assert context['result'] == context['value']


@then(parsers.re(r'the output is "(?P<expected>[\s\S]*)" and it loads back to the same string'))
def then_output_and_reloads(context: dict[str, Any], expected: str) -> None:
    """Assert the dumped output matches `expected` and reloads to the original scalar."""
    assert context['dumped'] == _decode(expected)
    assert syml.loads(context['dumped']) == context['value']


@then('dumping raises UnrepresentableValueError')
def then_raises_unrepresentable(context: dict[str, Any]) -> None:
    """Assert an `UnrepresentableValueError` was captured."""
    assert isinstance(context['error'], exc.UnrepresentableValueError)


@then(parsers.re(r'the output is "(?P<expected>[\s\S]*)"'))
def then_output_is(context: dict[str, Any], expected: str) -> None:
    """Assert the dumped output matches `expected` exactly."""
    assert context['dumped'] == _decode(expected)


@then('the output is the empty document and it loads back to the empty string')
def then_empty_document(context: dict[str, Any]) -> None:
    """Assert dumping the empty string yields the empty document, which reloads to it."""
    assert context['dumped'] == ''
    assert syml.loads(context['dumped']) == ''
