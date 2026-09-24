"""Bindings for specs/acceptance-specs/US00-smoke.feature (the reference example)."""

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

import syml

pytestmark = pytest.mark.acceptance

scenarios('US00-smoke.feature')


@given(parsers.parse('a SYML document containing "{text}"'))
def given_document(context: dict[str, Any], text: str) -> None:
    context['text'] = text


@when('it is parsed')
def when_parsed(context: dict[str, Any]) -> None:
    context['result'] = syml.loads(context['text'])


@then(parsers.parse('the result is a mapping with key "{key}" and value "{value}"'))
def then_mapping(context: dict[str, Any], key: str, value: str) -> None:
    assert context['result'] == {key: value}
