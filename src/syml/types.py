from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Union

from attrs import define
from parsimonious.nodes import Node as PNode

StrPath = Union[str, Path]

StrBool = Union[str, bool]


@define(slots=True, frozen=True)
class Pos:
    index: int
    line: int
    column: int


@define(slots=True, repr=False, frozen=True)
class Source:
    filename: Union[str, Path]
    start: Pos
    end: Pos
    text: str
    # value corresponds to a line of text
    value: StrBool

    @classmethod
    def from_node(cls, pnode: PNode, filename: StrPath = "", value: Optional[StrBool] = None) -> Source:
        from syml import utils

        return cls(
            filename=filename,
            start=utils.get_coords_of_str_index(pnode.full_text, pnode.start),
            end=utils.get_coords_of_str_index(pnode.full_text, pnode.end),
            text=pnode.text,
            value=value if value is not None else pnode.text,
        )

    @classmethod
    def from_text(
        cls,
        text: str,
        substring: str = None,
        source_text: Optional[str] = None,
        value: Optional[str] = None,
        filename: StrPath = "",
    ):
        from syml import utils

        if substring is None:
            substring = text
        match = re.search(substring, text)
        if match is None:
            raise ValueError(f"No match found for {substring!r}")
        source_text = match.group() if source_text is None else source_text
        return Source(
            filename=filename,
            start=utils.get_coords_of_str_index(text, match.start()),
            end=utils.get_coords_of_str_index(text, match.end()),
            text=source_text,
            value=value if value is not None else source_text,
        )

    def __repr__(self):
        return "%sLine %s, Column %s (index %s): %r (%r)" % (
            "%s, " % self.filename if self.filename else "",
            self.start.line,
            self.start.column,
            self.start.index,
            self.text,
            self.value,
        )

    def __str__(self):
        return self.text

    def __add__(self, other: SourceStr):
        if isinstance(other, str):
            lines = other.splitlines()
            return Source(
                filename=self.filename,
                start=self.start,
                end=Pos(index=self.end.index + len(other), line=self.end.line + len(lines), column=len(lines[-1])),
                text=self.text + other,
                value=str(self.value) + other,
            )
        elif isinstance(other, Source):
            return self + other.text


SourceStr = Union[Source, str]


SourceStrBool = Union[SourceStr, bool]
