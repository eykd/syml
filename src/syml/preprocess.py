"""Pre-processing pipeline for SYML documents (§9.0).

Applies the BOM-stripping, line-ending-normalization, and tab-indentation
scan steps to a raw document before parsing, while tracking a position map
back to the caller's original text.
"""

from __future__ import annotations

import dataclasses
import re
from bisect import bisect_left
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .basetypes import Pos
from .exceptions import EncodingError, TabIndentationError

if TYPE_CHECKING:  # pragma: nocover
    from .basetypes import Source, StrPath


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

    @staticmethod
    def line1_bom_offset(position_map: PositionMap | None, line: int) -> int:
        """Return `position_map.bom_offset` on line 1, `0` everywhere else (including `position_map is None`).

        The one `original-coordinate line/BOM -> ParseError(bom_offset=...)`
        step shared by every raise site that constructs a `ParseError` on
        possibly-BOM-shifted coordinates, so `ParseError.__str__` can centre
        its excerpt window on the right `line_text` index (D33, syml-cjk2.17).
        Off line 1 (or a normalized-text document with no BOM), the offset
        is always `0` and `position.column` already indexes `line_text`
        directly.
        """
        return position_map.bom_offset if position_map is not None and line == 1 else 0

    @staticmethod
    def map(pos: Pos, position_map: PositionMap | None) -> Pos:
        """Translate `pos` through `position_map.to_original`, or return it unchanged when there is no map.

        The one `raw Pos -> conditionally re-anchored Pos` step shared by every
        error-position construction site that has only a bare `Pos` (not a whole
        `Source`) to re-anchor onto the caller's original text (Contract 08,
        FR-013, R-02, US8). `Source`-shaped values go through
        `to_original_source` instead.
        """
        return pos if position_map is None else position_map.to_original(pos)

    def to_original_source(self, source: Source) -> Source:
        """Return `source` with its `start`/`end` translated into original-document coordinates.

        Shared by the quoted-value, unquoted-leaf, and key `Source`-construction
        paths (`parsers.py`, `nodes.py`) that all re-anchor a normalized-text
        `Source` onto the caller's original text (Contract 08, FR-013, R-02, US8).
        """
        return dataclasses.replace(source, start=self.to_original(source.start), end=self.to_original(source.end))


@dataclass(slots=True, frozen=True)
class Document:
    """The result of pre-processing a raw SYML document (§9.0 steps 1-3)."""

    original: str
    normalized: str
    position_map: PositionMap
    filename: StrPath | None


_LINE_ENDING = re.compile(r'\r\n|\r')
_LINE_ENDING_OR_LF = re.compile(r'\r\n|\r|\n')
_BOM = '﻿'


def is_blank(text: str) -> bool:
    """Return whether `text` is entirely U+0020/U+0009, in any mixture (§4.4, D14).

    An empty string is blank. Used by the step-3 tab scan to exempt
    blank lines from the leading-whitespace tab check.
    """
    return all(ch in ' \t' for ch in text)


def _scan_for_tab_indentation(
    normalized: str,
    position_map: PositionMap,
    filename: StrPath | None = None,
) -> None:
    """Raise `TabIndentationError` if any non-blank line has a tab in its leading-whitespace run.

    The raised error's `.position` is translated through `position_map` into
    the caller's original-text coordinates (through the BOM offset and CRLF
    position map), not the normalized-text coordinates the scan itself works
    in (Contract 03, FR-013).

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
                position_map.to_original(Pos(index=offset + column, line=line_number, column=column)),
                line,
                filename=filename,
                bom_offset=PositionMap.line1_bom_offset(position_map, line_number),
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


def encoding_error(err: UnicodeDecodeError, filename: StrPath | None) -> EncodingError:
    """Derive an `EncodingError` from a `UnicodeDecodeError` (Contract 05 §R-04).

    `err.start` is a byte offset; this converts it to code-point coordinates
    over `(err.object, err.start, err.encoding)` alone.

    :param err: The `UnicodeDecodeError` raised while decoding.
    :param filename: The filename to include in the message, if any.
    :returns: An `EncodingError` positioned at the first invalid byte.
    """
    prefix = err.object[: err.start].decode(err.encoding, errors='replace')
    index = len(prefix)
    breaks = list(_LINE_ENDING_OR_LF.finditer(prefix))
    line = 1 + len(breaks)
    last_break_end = breaks[-1].end() if breaks else 0
    column = index - last_break_end
    line_text = prefix[last_break_end:]
    bad_byte = err.object[err.start]
    return EncodingError(
        f'Invalid UTF-8 (byte 0x{bad_byte:02x}); save the file as UTF-8',
        Pos(index=index, line=line, column=column),
        line_text,
        filename=filename,
    )


def preprocess(text: str, filename: StrPath | None = None) -> Document:
    """Apply §9.0 steps 1-3 to `text`. Raises `TabIndentationError`."""
    bom_offset = 1 if text.startswith(_BOM) else 0
    stripped = text[bom_offset:]
    normalized, crlf_indices = _normalize_line_endings(stripped)
    position_map = PositionMap(bom_offset=bom_offset, crlf_indices=crlf_indices)
    _scan_for_tab_indentation(normalized, position_map, filename)
    return Document(
        original=text,
        normalized=normalized,
        position_map=position_map,
        filename=filename,
    )
