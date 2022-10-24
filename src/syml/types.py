from __future__ import annotations

from typing import TYPE_CHECKING, Union

from attrs import define

if TYPE_CHECKING:
    from pathlib import Path


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
    value: str

    def __repr__(self):
        return "%sLine %s, Column %s (index %s): %r (%r)" % (
            "%s, " % self.filename if self.filename else "",
            self.start.line,
            self.start.column,
            self.start.index,
            self.text,
            self.value,
        )
