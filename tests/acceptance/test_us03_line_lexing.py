"""Bindings for specs/acceptance-specs/US03-line-lexing.feature."""

import ast
import re
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

import syml

pytestmark = pytest.mark.acceptance

scenarios('US03-line-lexing.feature')

_ESCAPES = (
    (re.compile(r'\\+x([0-9a-fA-F]{2})'), lambda m: chr(int(m.group(1), 16))),
    (re.compile(r'\\+n'), '\n'),
    (re.compile(r'\\+t'), '\t'),
)


def _decode(raw: str) -> str:
    r"""Decode a feature file's backslash-escaped literal into real characters.

    Scenario text uses a mix of single- and double-backslash escape spelling,
    so each escape is matched on a run of one-or-more backslashes rather than
    a fixed count.
    """
    text = raw
    for pattern, replacement in _ESCAPES:
        text = pattern.sub(replacement, text)
    return text


@given(parsers.parse('a SYML document "{text}"'), target_fixture='document_text')
def given_document(text: str) -> str:
    return _decode(text)


@when('it is parsed')
def when_parsed(context: dict[str, Any], document_text: str) -> None:
    context['result'] = syml.loads(document_text)


@then(parsers.parse('the result equals {expected}'))
def then_result_equals(context: dict[str, Any], expected: str) -> None:
    assert context['result'] == ast.literal_eval(expected)


@then(parsers.parse('the result is the scalar "{text}"'))
def then_result_is_scalar(context: dict[str, Any], text: str) -> None:
    assert context['result'] == _decode(text)
