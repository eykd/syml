"""Bindings for specs/acceptance-specs/US04-empty-values.feature."""

import ast
import re
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

import syml

pytestmark = pytest.mark.acceptance

scenarios('US04-empty-values.feature')

_NEWLINE_ESCAPE = re.compile(r'\\+n')


def _decode(raw: str) -> str:
    r"""Decode the feature file's backslash-escaped "\\n" line-break marker.

    Scenario text may use a run of one-or-more backslashes before "n", so the
    escape is matched on that run rather than a fixed backslash count.
    """
    return _NEWLINE_ESCAPE.sub('\n', raw)


@given(parsers.parse('a SYML document "{text}"'), target_fixture='document_text')
def given_document(text: str) -> str:
    """Store the decoded document text."""
    return _decode(text)


@given('the empty document', target_fixture='document_text')
def given_empty_document() -> str:
    """Provide the empty document."""
    return ''


@when('it is parsed')
def when_parsed(context: dict[str, Any], document_text: str) -> None:
    """Parse the stored document text."""
    context['result'] = syml.loads(document_text)


@then(parsers.parse('the result equals {expected}'))
def then_result_equals(context: dict[str, Any], expected: str) -> None:
    """Assert the parsed result equals the given Python literal."""
    assert context['result'] == ast.literal_eval(expected)


@then('the result is the empty string')
def then_result_is_empty_string(context: dict[str, Any]) -> None:
    """Assert the parsed result is the empty string."""
    assert context['result'] == ''


def _assert_no_nulls(value: object) -> None:
    """Recursively assert no leaf in the given value is a language-level null."""
    if isinstance(value, dict):
        for item in value.values():
            _assert_no_nulls(item)
    elif isinstance(value, list):
        for item in value:
            _assert_no_nulls(item)
    else:
        assert value is not None


@then('no leaf value in the result is a null of any kind')
def then_no_leaf_is_null(context: dict[str, Any]) -> None:
    """Assert no leaf in the parsed result is None."""
    _assert_no_nulls(context['result'])
