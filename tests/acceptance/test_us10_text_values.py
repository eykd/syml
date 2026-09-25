"""Bindings for specs/acceptance-specs/US10-text-values.feature."""

import ast
import re
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

import syml
import syml.exceptions as exc

pytestmark = pytest.mark.acceptance

scenarios('US10-text-values.feature')

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

#: Undoes the table-cell backslash doubling in front of a literal `"` inside
#: a Python-source `expected` value, without disturbing an already-single
#: `\"` (which came from plain, non-table step text and is left for
#: `ast.literal_eval` to interpret as an escaped quote).
_DOUBLED_QUOTE_ESCAPE = re.compile(r'(\\+)"')


def _decode(raw: str) -> str:
    r"""Decode the feature file's backslash-escaped "\\n"/"\\xNN"/"\\uNNNN" markers."""
    text = raw
    for pattern, replacement in _ESCAPES:
        text = pattern.sub(replacement, text)
    return text


def _halve_doubled_quote_escapes(text: str) -> str:
    r"""Halve a table cell's doubled backslashes in front of `"`, leaving an odd run untouched."""

    def halve(match: re.Match[str]) -> str:
        backslashes = match.group(1)
        if len(backslashes) % 2 == 0:
            return backslashes[: len(backslashes) // 2] + '"'
        return match.group(0)

    return _DOUBLED_QUOTE_ESCAPE.sub(halve, text)


@given(parsers.parse('a SYML document "{text}"'))
def given_document(context: dict[str, Any], text: str) -> None:
    """Store the decoded document text."""
    context['text'] = _decode(text)


@when('it is parsed')
def when_parsed(context: dict[str, Any]) -> None:
    """Parse the stored document, capturing any raised parse error."""
    try:
        context['result'] = syml.loads(context['text'])
    except exc.ParseError as error:
        context['error'] = error


@then(parsers.re(r'the result equals (?P<expected>.+)'))
def then_result_equals(context: dict[str, Any], expected: str) -> None:
    """Assert the parsed result equals the given Python literal."""
    assert context['result'] == ast.literal_eval(_halve_doubled_quote_escapes(expected))


@then(parsers.re(r'the result is the scalar "(?P<expected>[\s\S]*)"'))
def then_result_is_scalar(context: dict[str, Any], expected: str) -> None:
    """Assert the parsed result equals the given scalar string."""
    assert context['result'] == _decode(expected)


@then(parsers.parse('parsing raises OutOfContextNodeError at line {line_number:d} with a key-pattern hint'))
def then_raises_with_key_pattern_hint(context: dict[str, Any], line_number: int) -> None:
    """Assert an `OutOfContextNodeError` at the given line whose message carries the key-pattern hint."""
    error = context['error']
    assert isinstance(error, exc.OutOfContextNodeError)
    assert error.position.line == line_number
    assert 'is not a key' in error.message


@then('parsing raises OutOfContextNodeError')
def then_raises_out_of_context(context: dict[str, Any]) -> None:
    """Assert an `OutOfContextNodeError` was captured."""
    assert isinstance(context['error'], exc.OutOfContextNodeError)
