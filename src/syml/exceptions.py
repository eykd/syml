"""Exceptions for parsing SYML documents"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: nocover
    from .basetypes import Pos, StrPath


class ParseError(ValueError):
    """An error encountered while parsing"""

    def __init__(self, message: str, *, filename: StrPath | None = None) -> None:
        self.filename = filename
        if filename:
            message = f'{filename}: {message}'
        super().__init__(message)


class OutOfContextNodeError(ParseError):
    """A node encountered in an illegal context"""

    def __init__(
        self,
        *,
        pos: Pos,
        line_text: str,
        filename: StrPath | None = None,
    ) -> None:
        self.pos = pos
        self.line_text = line_text
        location = f'{pos.line}:{pos.column}'
        message = f'{location}: unexpected indentation: {line_text.rstrip()}'
        super().__init__(message, filename=filename)
