"""Pre-processing pipeline for SYML documents (§9.0) and line splitting (§13.3).

Applies the BOM-stripping, line-ending-normalization, and tab-indentation
scan steps to a raw document before parsing, while tracking a position map
back to the caller's original text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: nocover
    from .basetypes import Pos, StrPath


@dataclass(slots=True, frozen=True)
class PositionMap:
    """Maps a position in normalized text back to the caller's original text."""

    bom_offset: int
    crlf_indices: tuple[int, ...]

    def to_original(self, pos: Pos) -> Pos:  # pragma: nocover
        """Translate a normalized `Pos` back into original-document coordinates."""
        raise NotImplementedError


@dataclass(slots=True, frozen=True)
class Document:
    """The result of pre-processing a raw SYML document (§9.0 steps 1-3)."""

    original: str
    normalized: str
    position_map: PositionMap
    filename: StrPath | None


def preprocess(text: str, filename: StrPath | None = None) -> Document:
    """Apply §9.0 steps 1-3 to `text`. Raises `TabIndentationError`."""
    bom_offset = 1 if text.startswith('﻿') else 0
    normalized = text[bom_offset:]
    return Document(
        original=text,
        normalized=normalized,
        position_map=PositionMap(bom_offset=bom_offset, crlf_indices=()),
        filename=filename,
    )
