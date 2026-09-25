"""Bindings for specs/acceptance-specs/US11-strict-structure-errors.feature."""

import ast
import re
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

import syml
import syml.exceptions as exc

pytestmark = pytest.mark.acceptance

scenarios('US11-strict-structure-errors.feature')

# Scenario Outline table cells come through pytest-bdd's gherkin parser with
# every literal backslash doubled (`Cell.from_dict`'s `_to_raw_string`), on
# top of the feature file's own "\\n"/"\\xNN"/"\\uNNNN" escape spelling; each
# pattern below matches a run of one-or-more backslashes so it decodes the
# same whether the text came from plain step text (single backslash) or a
# table cell (doubled backslash).
_ESCAPES = (
    (re.compile(r'\\+u([0-9a-fA-F]{4})'), lambda m: chr(int(m.group(1), 16))),
    (re.compile(r'\\+x([0-9a-fA-F]{2})'), lambda m: chr(int(m.group(1), 16))),
    (re.compile(r'\\+r'), '\r'),
    (re.compile(r'\\+n'), '\n'),
    (re.compile(r'\\+t'), '\t'),
)


def _decode(raw: str) -> str:
    r"""Decode the feature file's backslash-escaped "\\n"/"\\r"/"\\t"/"\\xNN"/"\\uNNNN" markers."""
    text = raw
    for pattern, replacement in _ESCAPES:
        text = pattern.sub(replacement, text)
    return text


@given(parsers.parse('a SYML document "{text}"'))
def given_document(context: dict[str, Any], text: str) -> None:
    """Store the decoded document text."""
    context['text'] = _decode(text)


@given(parsers.parse('a SYML document "{text}" loaded with filename "{filename}"'))
def given_document_with_filename(context: dict[str, Any], text: str, filename: str) -> None:
    """Store the decoded document text and the filename it is loaded with."""
    context['text'] = _decode(text)
    context['filename'] = filename


@when('it is parsed')
def when_parsed(context: dict[str, Any]) -> None:
    """Parse the stored document, capturing any raised parse error."""
    filename = context.get('filename')
    try:
        context['result'] = syml.loads(context['text'], filename=filename)
    except exc.ParseError as error:
        context['error'] = error


@then(parsers.re(r'the result equals (?P<expected>[\s\S]+)'))
def then_result_equals(context: dict[str, Any], expected: str) -> None:
    """Assert the parsed result equals the given Python literal."""
    assert context['result'] == ast.literal_eval(expected)


@then(parsers.re(r'the result is the scalar "(?P<expected>[\s\S]*)"'))
def then_result_is_scalar(context: dict[str, Any], expected: str) -> None:
    """Assert the parsed result equals the given scalar string."""
    assert context['result'] == _decode(expected)


@then('parsing raises OutOfContextNodeError')
def then_raises_out_of_context(context: dict[str, Any]) -> None:
    """Assert an `OutOfContextNodeError` was captured."""
    assert isinstance(context['error'], exc.OutOfContextNodeError)


@then('parsing raises OutOfContextNodeError with an indentation hint')
def then_raises_with_indentation_hint(context: dict[str, Any]) -> None:
    """Assert an `OutOfContextNodeError` whose message carries the sibling-indentation hint."""
    error = context['error']
    assert isinstance(error, exc.OutOfContextNodeError)
    assert "a list under a key must be indented past the key's column" in error.message


@then('parsing raises TabIndentationError')
def then_raises_tab_indentation(context: dict[str, Any]) -> None:
    """Assert a `TabIndentationError` was captured."""
    assert isinstance(context['error'], exc.TabIndentationError)


@then(
    parsers.re(
        r'parsing raises OutOfContextNodeError whose string form starts '
        r'"(?P<prefix>[^"]+)" naming open columns (?P<col1>\d+) and (?P<col2>\d+)'
    )
)
def then_raises_naming_open_columns(context: dict[str, Any], prefix: str, col1: str, col2: str) -> None:
    """Assert an `OutOfContextNodeError` whose `str()` starts with `prefix` and names both open columns."""
    error = context['error']
    assert isinstance(error, exc.OutOfContextNodeError)
    assert str(error).startswith(prefix)
    assert f'columns {col1} and {col2}' in error.message


@then(
    parsers.re(
        r'parsing raises an error whose string form starts "(?P<str_prefix>[^"]+)" '
        r'and whose message starts "(?P<message_prefix>[^"]+)"'
    )
)
def then_raises_with_str_and_message_prefix(context: dict[str, Any], str_prefix: str, message_prefix: str) -> None:
    """Assert the captured error's `str()` and `.message` both carry the given filename prefixes."""
    error = context['error']
    assert str(error).startswith(str_prefix)
    assert error.message.startswith(message_prefix)


@then(parsers.parse('parsing raises an error whose message starts "{message_prefix}"'))
def then_raises_with_message_prefix(context: dict[str, Any], message_prefix: str) -> None:
    """Assert the captured error's `.message` starts with the given filename prefix."""
    assert context['error'].message.startswith(message_prefix)


@then(parsers.parse('parsing raises TabIndentationError at index {index:d}, line {line:d}, column {column:d}'))
def then_raises_tab_indentation_at(context: dict[str, Any], index: int, line: int, column: int) -> None:
    """Assert a `TabIndentationError` positioned at the given original-text coordinates."""
    error = context['error']
    assert isinstance(error, exc.TabIndentationError)
    assert error.position.index == index
    assert error.position.line == line
    assert error.position.column == column
