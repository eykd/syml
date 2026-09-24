"""Exceptions for parsing SYML documents"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: nocover
    from .basetypes import Pos, StrPath


def error_message(description: str, filename: StrPath | None) -> str:
    """`description` alone when filename is None, else f'{filename}: {description}'."""
    if filename is None:
        return description
    return f'{filename}: {description}'


class ParseError(ValueError):
    """An error encountered while parsing"""

    # Contract 05 §Surface: the `message`/`position`/`line_text` attribute
    # contract (R-03).
    message: str
    position: Pos
    line_text: str

    def __init__(self, message: str, position: Pos, line_text: str, *extra: object) -> None:
        """Store `message`, `position`, and `line_text`, preserving `.args`."""
        super().__init__(message, position, line_text, *extra)
        self.message = message
        self.position = position
        self.line_text = line_text


class OutOfContextNodeError(ParseError):
    """A node encountered in an illegal context"""


class TabIndentationError(ParseError):
    """A tab character was found in a line's leading whitespace (§9.0.3)."""


class EncodingError(ParseError):
    """Invalid-byte input could not be decoded (§11.3, FR-009, R-04)."""


class MalformedQuotedStringError(ParseError):
    """A quoted string was unterminated, stranded, or carried a bad escape/code point (§8.5, §11.3)."""

    def __init__(
        self,
        message: str,
        position: Pos,
        line_text: str,
        escape: str | None,
        code_point: int | None,
    ) -> None:
        """Store the offending escape text and/or out-of-range code point, both nullable."""
        super().__init__(message, position, line_text, escape, code_point)
        self.escape = escape
        self.code_point = code_point


class DuplicateKeyError(ParseError):
    """A mapping key repeats an earlier sibling's key at the same level (FR-007, §8.3)."""

    def __init__(
        self,
        message: str,
        position: Pos,
        line_text: str,
        key: str,
        first_position: Pos,
    ) -> None:
        """Store the repeated key and the position of its first occurrence."""
        super().__init__(message, position, line_text, key, first_position)
        self.key = key
        self.first_position = first_position


class UnrepresentableValueError(ValueError):
    """A value has no SYML encoding (§11.2.2-.4). Raised by `dumps`, not a `ParseError`."""
