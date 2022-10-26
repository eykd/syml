from __future__ import annotations

from pathlib import Path
from typing import Union

from attrs import define

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

    # def __add__(self, other):
    #     if isinstance(other, str):
    #         lines = other.splitlines()
    #         return Source(
    #             filename=self.filename,
    #             start=self.start,
    #             end
    #         )


SourceStr = Union[Source, str]


SourceStrBool = Union[SourceStr, bool]
