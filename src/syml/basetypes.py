"""SYML base types"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from attrs import define

from syml import utils

if TYPE_CHECKING:  # pragma: nocover
    from parsimonious.nodes import Node as PNode


StrPath = str | Path

StrBool = str | bool


@define(slots=True, frozen=True)
class Pos:
    """A position within a source file"""

    index: int
    line: int
    column: int

    @classmethod
    def from_str_index(cls, text: str, index: int) -> Pos:
        """Get (line_number, col) of `index` in `string`.

        Based on http://stackoverflow.com/a/24495900
        """
        lines = utils.split_lines(text, keepends=True)
        curr_pos = 0
        for linenum, line in enumerate(lines):
            if curr_pos + len(line) > index:
                return cls(index, linenum + 1, index - curr_pos)
            curr_pos += len(line)
        return cls(len(text), linenum + 1, 0)


@define(slots=True, repr=False, frozen=True)
class Source:
    """A line within a source file"""

    filename: str | Path
    start: Pos
    end: Pos
    text: str
    # value corresponds to a line of text
    value: StrBool

    @classmethod
    def from_node(cls, pnode: PNode, filename: StrPath = '', value: StrBool | None = None) -> Source:
        """Build a Source from the given PNode, filename, and line value."""
        return cls(
            filename=filename,
            start=Pos.from_str_index(pnode.full_text, pnode.start),
            end=Pos.from_str_index(pnode.full_text, pnode.end),
            text=pnode.text,
            value=value if value is not None else pnode.text,
        )

    @classmethod
    def from_text(
        cls,
        text: str,
        substring: str | None = None,
        source_text: str | None = None,
        value: bool | str | None = None,  # noqa: FBT001
        filename: StrPath = '',
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
            value=value if value is not None else source_text,
        )

    def __repr__(self) -> str:
        filename = f'{self.filename}, ' if self.filename else ''
        return f'{filename}Line {self.start.line}, Column {self.start.column} (index {self.start.index}): {self.text!r} ({self.value!r})'

    def __str__(self) -> str:
        return self.text

    def __add__(self, other: SourceStr) -> Source:
        if isinstance(other, str):
            lines = utils.split_lines(other, keepends=True)
            return Source(
                filename=self.filename,
                start=self.start,
                end=Pos(index=self.end.index + len(other), line=self.end.line + len(lines), column=len(lines[-1])),
                text=self.text + other,
                value=str(self.value) + other,
            )
        if isinstance(other, Source):
            return self + other.text

        raise TypeError('Tried to add invalid type to Source', type(other))


SourceStr = Source | str


SourceStrBool = SourceStr | bool
