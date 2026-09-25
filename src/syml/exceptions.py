"""Exceptions for parsing SYML documents"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: nocover
    from .basetypes import Pos, StrPath


def error_message(description: str, filename: StrPath | None) -> str:
    """`description` alone when filename is None, else f'{filename}: {description}'."""
    if filename is None:
        return description
    return f'{filename}: {description}'


def _printable(text: str) -> str:
    """Replace every non-`str.isprintable()` character in `text` with its Python escape.

    Used to render `line_text` and `filename` in `ParseError.__str__` without
    echoing raw control characters, ANSI escapes, or lone surrogates onto the
    caller's terminal/stream (Contract 03 §Security).
    """
    return ''.join(ch if ch.isprintable() else repr(ch)[1:-1] for ch in text)


class ParseError(ValueError):
    """An error encountered while parsing"""

    # Contract 05 §Surface: the `message`/`position`/`line_text` attribute
    # contract (R-03).
    message: str
    position: Pos
    line_text: str

    def __init__(
        self,
        message: str,
        position: Pos,
        line_text: str,
        *extra: object,
        filename: StrPath | None = None,
    ) -> None:
        """Store `message`, `position`, and `line_text`, preserving `.args`.

        `message` is the bare description (no filename prefix). `filename`,
        when given, is normalized with `os.fspath` (`''` normalizes to
        `None`) and used both to build the prefixed `.message` and to render
        `__str__`'s `<filename>:` segment.
        """
        normalized_filename = os.fspath(filename) if filename else None
        full_message = error_message(message, normalized_filename)
        super().__init__(full_message, position, line_text, *extra)
        self.message = full_message
        self.position = position
        self.line_text = line_text
        self._description = message
        self._filename = normalized_filename

    def __str__(self) -> str:
        r"""Render `<filename>:<line>:<column>: <description>\n<line_text>` (Contract 03 §Surface).

        `<filename>:` is omitted when no filename is known. `<line>` is
        1-indexed, `<column>` 0-indexed, both taken from `self.position`
        (§10.2). The filename and line text are rendered through
        `_printable` so no non-printable character (including a stray
        newline in a caller-supplied filename) escapes into the two-line
        shape this format promises.
        """
        prefix = f'{_printable(self._filename)}:' if self._filename else ''
        return f'{prefix}{self.position.line}:{self.position.column}: {self._description}\n{_printable(self.line_text)}'


class OutOfContextNodeError(ParseError):
    """A node encountered in an illegal context"""


class TabIndentationError(ParseError):
    """A tab character was found in a line's leading whitespace (§9.0.3)."""


class EncodingError(ParseError):
    """Invalid-byte input could not be decoded (§11.3, FR-009, R-04)."""


class DuplicateKeyError(ParseError):
    """A mapping key repeats an earlier sibling's key at the same level (FR-007, §8.3)."""

    def __init__(
        self,
        message: str,
        position: Pos,
        line_text: str,
        key: str,
        first_position: Pos,
        *,
        filename: StrPath | None = None,
    ) -> None:
        """Store the repeated key and the position of its first occurrence."""
        super().__init__(message, position, line_text, key, first_position, filename=filename)
        self.key = key
        self.first_position = first_position


class UnrepresentableValueError(ValueError):
    """A value has no SYML encoding (§11.2.1-.3). Raised by `dumps`, not a `ParseError`."""
