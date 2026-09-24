"""Pre-processing pipeline for SYML documents (§9.0) and line splitting (§13.3).

Applies the BOM-stripping, line-ending-normalization, and tab-indentation
scan steps to a raw document before parsing, while tracking a position map
back to the caller's original text.
"""

from __future__ import annotations

import re
from bisect import bisect_left
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .basetypes import Pos
from .exceptions import EncodingError, TabIndentationError

if TYPE_CHECKING:  # pragma: nocover
    from .basetypes import StrPath


@dataclass(slots=True, frozen=True)
class PositionMap:
    """Maps a position in normalized text back to the caller's original text."""

    bom_offset: int
    crlf_indices: tuple[int, ...]

    def to_original(self, pos: Pos) -> Pos:
        """Translate a normalized `Pos` back into original-document coordinates."""
        index = pos.index + self.bom_offset + bisect_left(self.crlf_indices, pos.index)
        column = pos.column + self.bom_offset if pos.line == 1 else pos.column
        return Pos(index, pos.line, column)


@dataclass(slots=True, frozen=True)
class Document:
    """The result of pre-processing a raw SYML document (§9.0 steps 1-3)."""

    original: str
    normalized: str
    position_map: PositionMap
    filename: StrPath | None


_LINE_ENDING = re.compile(r'\r\n|\r')
_BOM = '﻿'


def is_blank(text: str) -> bool:
    """Return whether `text` is entirely U+0020/U+0009, in any mixture (§4.4, D14).

    An empty string is blank. The one shared blank predicate, used by both
    the step-3 tab scan and Contract 02's per-line loop.
    """
    return all(ch in ' \t' for ch in text)


def _scan_for_tab_indentation(normalized: str) -> None:
    """Raise `TabIndentationError` if any non-blank line has a tab in its leading-whitespace run.

    See §9.0.3, D14.
    """
    offset = 0
    for line_number, line in enumerate(normalized.split('\n'), start=1):
        if is_blank(line):
            offset += len(line) + 1
            continue
        run_text = line[: len(line) - len(line.lstrip(' \t'))]
        if '\t' in run_text:
            column = run_text.index('\t')
            raise TabIndentationError(
                "A tab character was found in a line's leading whitespace",
                Pos(index=offset + column, line=line_number, column=column),
                line,
            )
        offset += len(line) + 1


def _normalize_line_endings(text: str) -> tuple[str, tuple[int, ...]]:
    r"""Collapse CRLF and bare CR to LF in one left-to-right scan.

    Returns the normalized text plus the normalized-text indices where a
    `\r\n` pair collapsed into a single `\n` (needed by `PositionMap` to
    translate positions back to the original document).
    """
    chunks: list[str] = []
    crlf_indices: list[int] = []
    pos = 0
    out_pos = 0
    for match in _LINE_ENDING.finditer(text):
        start, end = match.span()
        chunks.append(text[pos:start])
        out_pos += start - pos
        if match.group() == '\r\n':
            crlf_indices.append(out_pos)
        chunks.append('\n')
        out_pos += 1
        pos = end
    chunks.append(text[pos:])
    return ''.join(chunks), tuple(crlf_indices)


def split_lines_lf(text: str) -> list[str]:
    """Split `text` into lines on U+000A only (§13.3, FR-003).

    Unlike `str.splitlines()`, this does not treat U+2028, U+2029, U+0085,
    U+000B, U+000C, or U+001C-U+001E as line terminators.
    """
    return text.split('\n')


def encoding_error(err: UnicodeDecodeError, filename: StrPath | None) -> EncodingError:
    """Derive an `EncodingError` from a `UnicodeDecodeError` (Contract 05 §R-04).

    `err.start` is a byte offset; this converts it to code-point coordinates
    over `(err.object, err.start, err.encoding)` alone.

    :param err: The `UnicodeDecodeError` raised while decoding.
    :param filename: The filename to include in the message, if any.
    :returns: An `EncodingError` positioned at the first invalid byte.
    """
    raise NotImplementedError


def preprocess(text: str, filename: StrPath | None = None) -> Document:
    """Apply §9.0 steps 1-3 to `text`. Raises `TabIndentationError`."""
    bom_offset = 1 if text.startswith(_BOM) else 0
    stripped = text[bom_offset:]
    normalized, crlf_indices = _normalize_line_endings(stripped)
    _scan_for_tab_indentation(normalized)
    return Document(
        original=text,
        normalized=normalized,
        position_map=PositionMap(bom_offset=bom_offset, crlf_indices=crlf_indices),
        filename=filename,
    )
