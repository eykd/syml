"""Bindings for specs/acceptance-specs/US02-preprocessing.feature."""

import ast
import re
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

import syml
import syml.exceptions

pytestmark = pytest.mark.acceptance

scenarios('US02-preprocessing.feature')

_ESCAPES = (
    (re.compile(r'\\+ufeff'), '\N{ZERO WIDTH NO-BREAK SPACE}'),
    (re.compile(r'\\+u2028'), '\N{LINE SEPARATOR}'),
    (re.compile(r'\\+r\\+n'), '\r\n'),
    (re.compile(r'\\+r'), '\r'),
    (re.compile(r'\\+n'), '\n'),
    (re.compile(r'\\+t'), '\t'),
)


def _decode(raw: str) -> str:
    r"""Decode the feature file's backslash-escaped literal into real characters.

    Scenario text uses a mix of single- and double-backslash escape spelling
    (e.g. both `﻿` and `\\r\\n`), so each escape is matched on a
    run of one-or-more backslashes rather than a fixed count.
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
    try:
        context['result'] = syml.loads(document_text)
    except syml.exceptions.ParseError as exc:
        context['error'] = exc


@then(parsers.parse('the result equals {expected}'))
def then_result_equals(context: dict[str, Any], expected: str) -> None:
    assert context['result'] == ast.literal_eval(expected)


@then('the result is the empty string')
def then_result_is_empty_string(context: dict[str, Any]) -> None:
    assert context['result'] == ''


@then(parsers.parse('parsing fails with "{exception_name}"'))
def then_parsing_fails(context: dict[str, Any], exception_name: str) -> None:
    error = context['error']
    assert type(error).__name__ == exception_name
