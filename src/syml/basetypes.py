"""SYML base types"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

from syml import utils

if TYPE_CHECKING:  # pragma: nocover
    from parsimonious.nodes import Node as PNode

    from syml.preprocess import PositionMap


StrPath = str | Path

# Contract 07 §Surface: `SymlData` is the recursive return type of `loads`;
# `SymlInput` is the deliberately widened parameter type of `dumps`/`dump`,
# because `list`/`dict` invariance would otherwise reject every typed caller.
type SymlData = str | list[SymlData] | dict[str, SymlData]
SymlInput = str | list[Any] | dict[str, Any]


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
        """
        parts = text.split('\n')
        lines = [part + '\n' for part in parts[:-1]]
        if parts[-1]:
            lines.append(parts[-1])
        curr_pos = 0
        linenum = 0
        for linenum, line in enumerate(lines):
            if curr_pos + len(line) > index:
                return cls(index, linenum + 1, index - curr_pos)
            curr_pos += len(line)
        return cls(len(text), linenum + 1, 0)


class Line(NamedTuple):
    """A single line of normalized text, its starting index, and its 1-based line number."""

    text: str
    start: int
    number: int


def pos_at(line: Line, offset: int) -> Pos:
    """Lift a line-local `offset` to a normalized `Pos` (Contract 01).

    Callers pass the result through `PositionMap.to_original` before it
    reaches a `Source` or `ParseError`.
    """
    return Pos(line.start + offset, line.number, offset)


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
        line: Line | None = None,
        position_map: PositionMap | None = None,
        filename: StrPath | None = None,
    ) -> Source:
        """Build a Source from the given PNode, filename, and line value.

        When `line` and `position_map` are given (Contract 08), each endpoint
        is built as `position_map.to_original(pos_at(line, offset))`, so the
        resulting positions land in the caller's original-document
        coordinates (BOM, CRLF, etc.) rather than the normalized text.
        Otherwise, falls back to `Pos.from_str_index` over `pnode.full_text`.
        """
        if line is not None and position_map is not None:
            return cls(
                filename=filename,
                start=position_map.to_original(pos_at(line, pnode.start)),
                end=position_map.to_original(pos_at(line, pnode.end)),
                text=pnode.text,
            )
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
        if substring is None:  # pragma: no cover
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
            lines = utils.split_lines(other, keepends=True)
            return Source(
                filename=self.filename,
                start=self.start,
                end=Pos(index=self.end.index + len(other), line=self.end.line + len(lines), column=len(lines[-1])),
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
        return str(self) == str(other)

    def __hash__(self) -> int:  # pragma: no cover
        return hash(str(self))


SourceStr = Source | str
