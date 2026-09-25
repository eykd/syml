"""Verifies README.md's lead example against the live parser (Contract 06 obligation 6).

Extracts the ``document`` string from the first fenced ```python block and
the printed result from the second, then asserts ``syml.loads(document)``
equals the printed result -- so the README's first example cannot again
drift from the parser (red team outer iteration 4).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

import syml
from syml.basetypes import Source

README_PATH = Path(__file__).parent.parent / 'README.md'


def _first_two_python_blocks(text: str) -> tuple[str, str]:
    """Return the raw contents of the first two fenced ```python blocks."""
    blocks: list[str] = []
    lines = text.split('\n')
    index = 0
    total = len(lines)
    while index < total and len(blocks) < 2:
        if lines[index].strip() != '``` python':
            index += 1
            continue
        close = index + 1
        while lines[close].strip() != '```':
            close += 1
        blocks.append('\n'.join(lines[index + 1 : close]))
        index = close + 1
    assert len(blocks) == 2, 'expected at least two fenced ```python blocks in README.md'
    return blocks[0], blocks[1]


def _extract_document(block: str) -> str:
    """Pull the ``document`` triple-quoted string's contents out of the first fenced block."""
    start = block.index('"""') + len('"""')
    end = block.index('"""', start)
    return block[start:end]


def _extract_printed_result(block: str) -> object:
    """Reconstruct the Python value printed by the second block's ``>>> syml.loads(document)`` call."""
    result_lines = [line for line in block.split('\n') if not line.startswith('>>>') and line.strip() != '']
    return ast.literal_eval('\n'.join(result_lines))


def test_the_readme_lead_example_matches_what_loads_actually_returns() -> None:
    """README's first document/result pair stays in sync with the shipped parser."""
    readme_text = README_PATH.read_text(encoding='utf-8')
    document_block, result_block = _first_two_python_blocks(readme_text)
    document = _extract_document(document_block)
    expected = _extract_printed_result(result_block)

    assert syml.loads(document) == expected


def test_the_readme_source_truthiness_example_is_runnable() -> None:
    """README's `Source` section states a runnable expression, not `Source(text=...)` (syml-cjk2.4)."""
    readme_text = README_PATH.read_text(encoding='utf-8')
    match = re.search(r'`(bool\(Source\.from_text\(\'\'\)\))` is `True`', readme_text)
    assert match is not None, "expected the README's empty-Source-is-truthy example to be present"

    assert eval(match.group(1), {'Source': Source}) is True  # noqa: S307
    with pytest.raises(TypeError):
        len(Source.from_text(''))  # type: ignore[arg-type]
