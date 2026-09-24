"""SYML base types"""

from __future__ import annotations

import re
from bisect import bisect_right
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: nocover
    from collections.abc import Iterator

    from parsimonious.nodes import Node as PNode

    from syml.preprocess import PositionMap


StrPath = str | Path

# Contract 07 §Surface: `SymlData` is the recursive return type of `loads`;
# `SymlInput` is the deliberately widened parameter type of `dumps`/`dump`,
# because `list`/`dict` invariance would otherwise reject every typed caller.
type SymlData = str | list[SymlData] | dict[str, SymlData]
SymlInput = str | list[Any] | dict[str, Any]

# Scoped, per-parse cache for `_line_start_offsets` (see below): `None` outside
# a `_line_offset_cache_scope()` block, and a fresh `dict` for the duration of
# one `parsers.parse()` call otherwise. Keyed by `id(text)` rather than `text`
# itself so the cache never pins a document's text alive: the same `text`
# object is held alive for the whole scope anyway (by the parse tree that owns
# it), so `id()` cannot be recycled onto a different string within one scope.
_line_offset_cache: ContextVar[dict[int, tuple[tuple[int, ...], bool]] | None] = ContextVar(
    '_line_offset_cache', default=None
)


@contextmanager
def _line_offset_cache_scope() -> Iterator[None]:
    """Scope `_line_start_offsets`'s cache to one parse (sp:security-review, harden cycle 2, syml-x0m.6.2).

    A process-global `lru_cache` keyed on document text pinned up to 4 full
    documents (plus their line-offset tables) in memory for the life of the
    process, well after every caller had dropped its own reference. Scoping
    the cache to a single `parsers.parse()` call via a `ContextVar` keeps the
    O(1)-amortized-per-node win (`Source.from_node` calls `Pos.from_str_index`
    twice per parsed node over the same `pnode.full_text`) without retaining
    anything once that call returns.
    """
    token = _line_offset_cache.set({})
    try:
        yield
    finally:
        _line_offset_cache.reset(token)


def _line_start_offsets(text: str) -> tuple[tuple[int, ...], bool]:
    r"""Return per-line start offsets in `text`, plus whether the last line lacks a trailing ``\n``.

    Cached for the duration of the enclosing `_line_offset_cache_scope()` (if
    any), keyed on `id(text)`, because `Pos.from_str_index` is called twice
    per parsed node from `Source.from_node` over the same `pnode.full_text`
    object: without caching, a document with O(n) nodes recomputed this O(n)
    scan on every call, making parsing O(n^2) overall. Outside a scope (e.g.
    direct calls to `Pos.from_str_index` in tests or one-shot error paths),
    every call recomputes -- there is nothing to cache into.

    Mirrors the line-splitting semantics `Pos.from_str_index` has always had:
    counts lines by ``\n`` only (SYML §13.3), and a trailing ``\n`` (or empty
    `text`) does not start a new, separately-addressable line.
    """
    cache = _line_offset_cache.get()
    key = id(text)
    if cache is not None and key in cache:
        return cache[key]
    result = _compute_line_start_offsets(text)
    if cache is not None:
        cache[key] = result
    return result


def _compute_line_start_offsets(text: str) -> tuple[tuple[int, ...], bool]:
    r"""Do the actual O(n) scan `_line_start_offsets` caches the result of.

    Split out so tests can spy on cache misses directly (a cache hit never
    reaches this function), rather than on `_line_start_offsets` itself, which
    is called on every `Pos.from_str_index` invocation regardless of whether
    the underlying scan is skipped.
    """
    starts = [0, *(match.end() for match in re.finditer('\n', text))]
    if text == '' or text.endswith('\n'):
        starts.pop()
    ends_without_newline = bool(starts) and not text.endswith('\n')
    return tuple(starts), ends_without_newline


@dataclass(slots=True, frozen=True)
class Pos:
    """A position within a source file"""

    index: int
    line: int
    column: int

    @classmethod
    def from_str_index(cls, text: str, index: int) -> Pos:
        r"""Get (line_number, col) of `index` in `string`.

        Counts lines by splitting on ``\n`` only (SYML §13.3): other Unicode
        line-break characters (e.g. U+2028) do not terminate a line.

        Resolves the line via a cached, O(log n) bisect over `text`'s line
        start offsets (see `_line_start_offsets`) rather than rescanning
        `text` on every call.
        """
        starts, ends_without_newline = _line_start_offsets(text)
        if not starts:
            return cls(len(text), 1, 0)
        linenum = bisect_right(starts, index) - 1
        line_start = starts[linenum]
        is_last_line = linenum == len(starts) - 1
        line_len = (starts[linenum + 1] - line_start) if not is_last_line else (len(text) - line_start)
        at_unterminated_end = is_last_line and ends_without_newline and line_start + line_len == index
        if line_start + line_len > index or at_unterminated_end:
            return cls(index, linenum + 1, index - line_start)
        return cls(len(text), linenum + 1, 0)


def get_line_text(text: str, line_number: int) -> str:
    r"""Return the 1-indexed `line_number`'s text from `text`, terminator excluded.

    Splits on ``\n`` only (SYML §13.3): other Unicode line-break characters
    (e.g. U+2028) do not terminate a line, matching `Pos.from_str_index`.
    Returns ``''`` for an out-of-range `line_number`.
    """
    lines = text.split('\n')
    index = line_number - 1
    if 0 <= index < len(lines):
        return lines[index]
    return ''


def map_pos(pos: Pos, position_map: PositionMap | None) -> Pos:
    """Translate `pos` through `position_map.to_original`, or return it unchanged when there is no map.

    The one `raw Pos -> conditionally re-anchored Pos` step shared by every
    error-position construction site that has only a bare `Pos` (not a whole
    `Source`) to re-anchor onto the caller's original text (Contract 08,
    FR-013, R-02, US8). `Source`-shaped values go through
    `PositionMap.to_original_source` instead.
    """
    return pos if position_map is None else position_map.to_original(pos)


@dataclass(slots=True, repr=False, frozen=True)
class Source:
    """A line within a source file"""

    filename: StrPath | None
    start: Pos
    end: Pos
    text: str

    @classmethod
    def from_node(
        cls,
        pnode: PNode,
        filename: StrPath | None = None,
    ) -> Source:
        """Build a Source from the given PNode and filename.

        Positions are computed via `Pos.from_str_index` over `pnode.full_text`
        (normalized-text coordinates). Callers that need original-text
        coordinates (Contract 08, FR-013, R-02) re-anchor the resulting
        `Source` through `PositionMap.to_original_source` afterward.
        """
        return cls(
            filename=filename,
            start=Pos.from_str_index(pnode.full_text, pnode.start),
            end=Pos.from_str_index(pnode.full_text, pnode.end),
            text=pnode.text,
        )

    @classmethod
    def from_text(
        cls,
        text: str,
        substring: str | None = None,
        source_text: str | None = None,
        filename: StrPath | None = None,
    ) -> Source:
        """Build a Source from the given components."""
        if substring is None:
            substring = text
        match = re.search(substring, text)
        if match is None:
            raise ValueError('No match found', substring)
        source_text = match.group() if source_text is None else source_text
        return Source(
            filename=filename,
            start=Pos.from_str_index(text, match.start()),
            end=Pos.from_str_index(text, match.end()),
            text=source_text,
        )

    def __repr__(self) -> str:
        filename = f'{self.filename}, ' if self.filename else ''
        return f'<Source: {filename}Line {self.start.line}, Column {self.start.column} (index {self.start.index}): {self.text!r}>'

    def __str__(self) -> str:
        return self.text

    def __add__(self, other: SourceStr) -> Source:
        if isinstance(other, str):
            lines = other.split('\n')  # LF only (§13.3), never splitlines
            return Source(
                filename=self.filename,
                start=self.start,
                end=Pos(
                    index=self.end.index + 1 + len(other),  # +1: the joining '\n'
                    line=self.end.line + len(lines),
                    column=len(lines[-1]),
                ),
                text=f'{self.text}\n{other}',
            )
        if isinstance(other, Source):
            return Source(
                filename=self.filename,
                start=self.start,
                end=other.end,
                text=f'{self.text}\n{other}',
            )

        raise TypeError('Tried to add invalid type to Source', type(other))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Source):
            return self.text == other.text
        if isinstance(other, str):
            return self.text == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.text)


SourceStr = Source | str
