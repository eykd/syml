"""Bindings for specs/acceptance-specs/US05-error-taxonomy.feature."""

from __future__ import annotations

import io
import re
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

import syml
import syml.exceptions as exc

pytestmark = pytest.mark.acceptance

scenarios('US05-error-taxonomy.feature')

_NEWLINE_ESCAPE = re.compile(r'\\+n')

# Documents drawn from the 2026-09-14 spec-conformance audit's list of inputs
# that used to leak a third-party (parsimonious) exception out of `loads`
# (gaps #1, #7, #9, #12) or that exercise the taxonomy's other raise sites
# (gaps #3, #10, #8/#9). Every one of these must now either succeed or raise
# a `syml.ParseError` subclass -- never anything else.
AUDIT_FAILING_SET = [
    'key:value',
    'key:"value"',
    'key:\tv',
    'key: \tv',
    'key: ',
    '- ',
    'a:\n        \n  b: c\n  d: e',
    '\ufeffkey: value',
    'a: b\r\nc: d',
    'key: value1\nkey: value2',
    '\tkey: value',
    'a: 1\n  - foo\nc: 1\n',
]


def _decode(raw: str) -> str:
    r"""Decode the feature file's backslash-escaped "\\n" line-break marker."""
    return _NEWLINE_ESCAPE.sub('\n', raw)


@given('the installed library')
def given_installed_library() -> None:
    """No setup needed: `syml` is already imported at module scope."""


@when(
    '"ParseError", "OutOfContextNodeError", "DuplicateKeyError", "TabIndentationError", '
    '"UnrepresentableValueError", and "EncodingError" are imported from syml',
    target_fixture='imported',
)
def when_six_imported() -> dict[str, type[Exception]]:
    """Import the six named exception classes from the top-level `syml` package."""
    names = [
        'ParseError',
        'OutOfContextNodeError',
        'DuplicateKeyError',
        'TabIndentationError',
        'UnrepresentableValueError',
        'EncodingError',
    ]
    return {name: getattr(syml, name) for name in names}


@then('all six resolve and their inheritance matches section 11.3 as amended')
def then_inheritance_matches(imported: dict[str, type[Exception]]) -> None:
    """Assert the taxonomy's base class and the §11.3 inheritance shape."""
    assert issubclass(imported['ParseError'], ValueError)
    for name in (
        'OutOfContextNodeError',
        'DuplicateKeyError',
        'TabIndentationError',
        'EncodingError',
    ):
        assert issubclass(imported[name], imported['ParseError'])
    # `UnrepresentableValueError` is raised by `dumps`, not a `ParseError`.
    assert issubclass(imported['UnrepresentableValueError'], ValueError)
    assert not issubclass(imported['UnrepresentableValueError'], imported['ParseError'])
    # D18 removed quoted strings, and with them `MalformedQuotedStringError`.
    assert not hasattr(syml, 'MalformedQuotedStringError')
    assert not hasattr(exc, 'MalformedQuotedStringError')


@given(parsers.parse('a SYML document "{text}"'), target_fixture='document_text')
def given_document(text: str) -> str:
    """Store the decoded document text."""
    return _decode(text)


@given("every document in the audit's failing set", target_fixture='documents')
def given_audit_failing_set() -> list[str]:
    """Provide the curated set of documents that used to leak third-party exceptions."""
    return list(AUDIT_FAILING_SET)


@when('it is parsed')
def when_parsed(context: dict[str, Any], document_text: str) -> None:
    """Parse the stored document text, capturing any raised parse error."""
    try:
        context['result'] = syml.loads(document_text)
    except exc.ParseError as error:
        context['error'] = error


@when('each is passed to loads')
def when_each_passed_to_loads(context: dict[str, Any], documents: list[str]) -> None:
    """Parse every document, recording the outcome (result or exception) for each."""
    outcomes: list[tuple[str, BaseException | None]] = []
    for document in documents:
        try:
            syml.loads(document)
        except BaseException as error:  # noqa: BLE001 - must observe every escaping type
            outcomes.append((document, error))
        else:
            outcomes.append((document, None))
    context['outcomes'] = outcomes


@then('any exception raised is a ParseError and no third-party parser exception escapes')
def then_only_parse_errors_escape(context: dict[str, Any]) -> None:
    """Assert every raised exception (if any) is a `syml.ParseError`."""
    for document, error in context['outcomes']:
        if error is not None:
            assert isinstance(error, exc.ParseError), (document, type(error))


@then(parsers.parse('the result is the scalar "{expected}"'))
def then_result_is_scalar(context: dict[str, Any], expected: str) -> None:
    """Assert the parsed result equals the given scalar string."""
    assert context['result'] == _decode(expected)


@then(parsers.parse('parsing fails with "{error_name}"'))
def then_parsing_fails(context: dict[str, Any], error_name: str) -> None:
    """Assert the captured error is an instance of the named exception class."""
    error_class = getattr(exc, error_name)
    assert isinstance(context['error'], error_class)


@then('the exception\'s "message", "position", and "line_text" are readable as named attributes')
def then_message_position_line_text_readable(context: dict[str, Any]) -> None:
    """Assert the three attributes are readable and non-empty/well-typed."""
    error = context['error']
    assert isinstance(error.message, str)
    assert error.message
    assert error.position is not None
    assert isinstance(error.line_text, str)


@then("the exception also carries the repeated key and the first occurrence's position")
def then_duplicate_key_details(context: dict[str, Any]) -> None:
    """Assert the `DuplicateKeyError` carries `.key` and `.first_position`."""
    error = context['error']
    assert error.key == 'key'
    assert error.first_position.line == 1


@given(parsers.parse('a binary file handle over the UTF-8 bytes of "{text}"'), target_fixture='binary_handle')
def given_binary_handle_over_utf8(text: str) -> io.BytesIO:
    """Provide a binary file handle over the UTF-8-encoded document text."""
    return io.BytesIO(_decode(text).encode('utf-8'))


@given('a binary file handle over bytes that are not valid UTF-8', target_fixture='binary_handle')
def given_binary_handle_over_invalid_utf8() -> io.BytesIO:
    """Provide a binary file handle over bytes that are not valid UTF-8."""
    return io.BytesIO(b'key: \xff\xfe value')


@given(parsers.parse('a text file handle over "{text}"'), target_fixture='text_handle')
def given_text_handle(text: str) -> io.StringIO:
    """Provide a text file handle over the given document text."""
    return io.StringIO(_decode(text))


@when('each is passed to load')
def when_each_passed_to_load(context: dict[str, Any], binary_handle: io.BytesIO, text_handle: io.StringIO) -> None:
    """Load both the binary and the text handle, storing both results."""
    context['binary_result'] = syml.load(binary_handle)
    context['text_result'] = syml.load(text_handle)


@when('it is passed to load')
def when_passed_to_load(context: dict[str, Any], binary_handle: io.BytesIO) -> None:
    """Load the binary handle, capturing any raised parse error."""
    try:
        context['result'] = syml.load(binary_handle)
    except exc.ParseError as error:
        context['error'] = error


@then('both results are equal')
def then_both_results_equal(context: dict[str, Any]) -> None:
    """Assert the binary-handle and text-handle results are equal."""
    assert context['binary_result'] == context['text_result']


@then('no replacement characters or unpaired surrogates appear in any result')
def then_no_replacement_characters(context: dict[str, Any]) -> None:
    """Assert loading raised before producing any result carrying replacement data."""
    assert 'result' not in context
