"""Bindings for specs/acceptance-specs/US01-tree-building-acceptance.feature."""

import ast
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

import syml
import syml.exceptions

pytestmark = pytest.mark.acceptance

scenarios('US01-tree-building-acceptance.feature')


@given(parsers.parse('a SYML document "{text}"'))
def given_document(context: dict[str, Any], text: str) -> None:
    r"""Store the document text, unescaping the "\\n" line-break marker."""
    context['text'] = text.replace('\\\\n', '\n')


@when('it is parsed')
def when_parsed(context: dict[str, Any]) -> None:
    """Parse the stored document, capturing any raised parse error."""
    try:
        context['result'] = syml.loads(context['text'])
    except syml.exceptions.ParseError as exc:
        context['error'] = exc


@then(parsers.re(r'the result equals (?P<expected>.+)'))
def then_result_equals(context: dict[str, Any], expected: str) -> None:
    """Assert the parsed result equals the given Python literal."""
    assert context['result'] == ast.literal_eval(expected)


@then(parsers.parse('parsing fails with "{error_name}"'))
def then_parsing_fails(context: dict[str, Any], error_name: str) -> None:
    """Assert the captured error is an instance of the named exception class."""
    error_class = getattr(syml.exceptions, error_name)
    assert isinstance(context['error'], error_class)
