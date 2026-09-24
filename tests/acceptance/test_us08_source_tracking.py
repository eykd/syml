"""Bindings for specs/acceptance-specs/US08-source-tracking.feature."""

import re
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

import syml
from syml.basetypes import Source

pytestmark = pytest.mark.acceptance

scenarios('US08-source-tracking.feature')

_ESCAPES = (
    (re.compile(r'\\+ufeff'), '\N{ZERO WIDTH NO-BREAK SPACE}'),
    (re.compile(r'\\+u2028'), '\N{LINE SEPARATOR}'),
    (re.compile(r'\\+r\\+n'), '\r\n'),
    (re.compile(r'\\+r'), '\r'),
    (re.compile(r'\\+n'), '\n'),
    (re.compile(r'\\+t'), '\t'),
)


def _decode(raw: str) -> str:
    r"""Decode the feature file's backslash-escaped literal into real characters."""
    text = raw
    for pattern, replacement in _ESCAPES:
        text = pattern.sub(replacement, text)
    return text


def _walk_sources(value: Any) -> list[Source]:  # noqa: ANN401
    """Flatten an as_source() tree into the list of every Source it contains, keys included."""
    sources: list[Source] = []
    if isinstance(value, Source):
        sources.append(value)
    elif isinstance(value, dict):
        for key, val in value.items():
            sources.append(key)
            sources.extend(_walk_sources(val))
    elif isinstance(value, list):
        for item in value:
            sources.extend(_walk_sources(item))
    return sources


@given(parsers.parse('a SYML document "{text}"'), target_fixture='document_text')
def given_document(text: str) -> str:
    return _decode(text)


@given('the released library')
def given_released_library() -> None:
    """No setup needed: the coverage/pragma check below reads the checked-in source tree."""


@when('it is parsed with source tracking')
def when_parsed_with_source_tracking(context: dict[str, Any], document_text: str) -> None:
    context['root'] = syml.parse(document_text, filename='doc.syml')


@when('the source-tracking surface is exercised')
def when_source_tracking_surface_is_exercised() -> None:
    """No action needed: the following Then reads the static source tree directly."""


@then('every leaf of as_source is a Source carrying a filename and start and end positions')
def then_every_leaf_is_a_source(context: dict[str, Any]) -> None:
    sources = _walk_sources(context['root'].as_source())
    assert sources, 'expected at least one Source in the tree'
    for source in sources:
        assert isinstance(source, Source)
        assert source.filename == 'doc.syml'
        assert source.start is not None
        assert source.end is not None


@then('as_data returns the equivalent plain strings, lists, and mappings')
def then_as_data_matches(context: dict[str, Any]) -> None:
    root = context['root']

    def to_plain(value: Any) -> Any:  # noqa: ANN401
        if isinstance(value, Source):
            return str(value)
        if isinstance(value, dict):
            return {str(key): to_plain(val) for key, val in value.items()}
        if isinstance(value, list):
            return [to_plain(item) for item in value]
        return value

    assert to_plain(root.as_source()) == root.as_data()


@then("the value's position locates it in the original text, counting the mark")
def then_value_position_counts_the_mark(context: dict[str, Any], document_text: str) -> None:
    src = context['root'].as_source()
    value_source = next(iter(src.values()))
    assert document_text[value_source.start.index : value_source.end.index] == value_source.text


@then("the value's position locates it in the original text, counting each carriage return")
def then_value_position_counts_crlf(context: dict[str, Any], document_text: str) -> None:
    src = context['root'].as_source()
    value_source = list(src.values())[1]
    assert document_text[value_source.start.index : value_source.end.index] == value_source.text


@then(parsers.parse('"{key}"\'s position reports line {line_number:d}'))
def then_keys_position_reports_line(context: dict[str, Any], key: str, line_number: int) -> None:
    src = context['root'].as_source()
    for source_key in src:
        if str(source_key) == key:
            assert source_key.start.line == line_number
            return
    pytest.fail(f'no key {key!r} found in as_source()')


_PRAGMA_RE = re.compile(r'pragma: no ?(cover|branch)')


@then('it is covered by tests rather than exempted from the coverage gate')
def then_not_exempted_from_coverage() -> None:
    """Contract 08 §Coverage: only `TYPE_CHECKING` blocks may carry a coverage pragma in `src/`."""
    src_root = Path(__file__).resolve().parents[2] / 'src'
    offenders = [
        f'{path}:{lineno}:{line}'
        for path in sorted(src_root.rglob('*.py'))
        for lineno, line in enumerate(path.read_text().splitlines(), start=1)
        if _PRAGMA_RE.search(line) and 'TYPE_CHECKING' not in line
    ]
    assert not offenders, f'pragma found outside TYPE_CHECKING blocks: {offenders}'
