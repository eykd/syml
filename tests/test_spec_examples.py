"""Executes every fenced ```syml example in SYML-SPECIFICATION.md (FR-001, SC-001).

The hand-transcribed Gherkin acceptance suites under ``tests/acceptance`` are
transcribed from ``specs/001-syml-1-0-conformance/spec.md``'s Acceptance
Scenarios, not extracted from ``SYML-SPECIFICATION.md``'s fenced blocks
(research.md §R-08: "distinct jobs"). This module is the only thing that
extracts directly from the specification text itself: every fenced ```syml
block immediately followed by a stated **Output:** or **ERROR:**-shaped
output must produce (or raise) exactly that from ``syml.loads()``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

import syml

SPEC_PATH = Path(__file__).parent.parent / 'SYML-SPECIFICATION.md'

#: SC-001's documented count (54) as of the 2026-09-24 D18/D19 spec amendment;
#: guards against the extractor's regexes silently matching zero blocks and
#: passing vacuously.
MINIMUM_EXAMPLE_COUNT = 54

_OUTPUT_HEADER_RE = re.compile(r'\*\*Output[^*]*\*\*\s*(.*)$')
_INLINE_CODE_RE = re.compile(r'`([^`]*)`')


@dataclass(frozen=True)
class SpecExample:
    """One fenced ```syml example paired with its stated Output or ERROR."""

    line_number: int
    source: str
    expected_json: str | None
    expected_exception_name: str | None


def _find_stated_output(lines: list[str], after_fence: int) -> str | None:
    """Return the stated Output/ERROR content following a closed fenced block, if any.

    `after_fence` is the index of the fence's closing ``` line. Returns
    `None` if the block is not immediately followed (blank lines skipped)
    by a ``**Output...**`` header, or if that header's content cannot be
    resolved (neither an inline code span nor a following ```json fence).
    """
    total = len(lines)
    cursor = after_fence + 1
    while cursor < total and lines[cursor].strip() == '':
        cursor += 1
    if cursor >= total:
        return None

    header_match = _OUTPUT_HEADER_RE.match(lines[cursor].strip())
    if header_match is None:
        return None

    rest = header_match.group(1).strip()
    if rest:
        code_match = _INLINE_CODE_RE.match(rest)
        return code_match.group(1) if code_match is not None else None

    fence_cursor = cursor + 1
    while fence_cursor < total and lines[fence_cursor].strip() == '':
        fence_cursor += 1
    if fence_cursor >= total or lines[fence_cursor].strip() != '```json':
        return None
    json_start = fence_cursor + 1
    json_close = json_start
    while lines[json_close].strip() != '```':
        json_close += 1
    return '\n'.join(lines[json_start:json_close])


def _example_from_content(line_number: int, source: str, content: str) -> SpecExample:
    """Build a `SpecExample`, distinguishing an ``ERROR:``-shaped content from JSON."""
    if content.startswith('ERROR:'):
        exception_name = content[len('ERROR:') :].strip().split(':')[0].strip()
        return SpecExample(
            line_number=line_number,
            source=source,
            expected_json=None,
            expected_exception_name=exception_name,
        )
    return SpecExample(
        line_number=line_number,
        source=source,
        expected_json=content,
        expected_exception_name=None,
    )


def extract_spec_examples(spec_text: str) -> list[SpecExample]:
    """Parse every fenced ```syml block in `spec_text` paired with its Output/ERROR.

    A block only becomes an example if it is immediately followed (blank
    lines skipped) by a ``**Output...**`` line, per §4.2/§8's convention.
    Blocks with no such line (purely illustrative fragments) are skipped.
    The stated output is either an inline code span on the header line
    itself, or a following fenced ```json block. A code span whose content
    begins with ``ERROR:`` names the exception class `loads()` must raise;
    otherwise the content is JSON describing the expected `loads()` result.
    """
    lines = spec_text.split('\n')
    total = len(lines)
    examples: list[SpecExample] = []
    index = 0
    while index < total:
        if lines[index].strip() != '```syml':
            index += 1
            continue
        block_start = index
        close = index + 1
        while lines[close].strip() != '```':
            close += 1
        source = '\n'.join(lines[block_start + 1 : close])
        if source:
            source += '\n'

        content = _find_stated_output(lines, close)
        if content is not None:
            examples.append(_example_from_content(block_start + 1, source, content))
        index = close + 1
    return examples


SPEC_EXAMPLES = extract_spec_examples(SPEC_PATH.read_text(encoding='utf-8'))


def test_at_least_the_documented_minimum_of_spec_examples_were_found() -> None:
    """Guard against the extractor silently matching zero blocks (SC-001)."""
    assert len(SPEC_EXAMPLES) >= MINIMUM_EXAMPLE_COUNT


@pytest.mark.parametrize(
    'example',
    SPEC_EXAMPLES,
    ids=[f'L{example.line_number}' for example in SPEC_EXAMPLES],
)
def test_spec_example_produces_its_stated_output(example: SpecExample) -> None:
    """Every fenced example's stated Output/ERROR is exactly what `loads()` produces."""
    if example.expected_exception_name is not None:
        exception_type: type[BaseException] = getattr(syml, example.expected_exception_name)
        with pytest.raises(exception_type):
            syml.loads(example.source)
    else:
        assert example.expected_json is not None
        expected = json.loads(example.expected_json)
        assert syml.loads(example.source) == expected
