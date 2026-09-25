"""Exceptions for parsing SYML documents"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: nocover
    from collections.abc import Sequence

    from .basetypes import Pos, StrPath


def error_message(description: str, filename: StrPath | None) -> str:
    """`description` alone when filename is None, else f'{filename}: {description}'."""
    if filename is None:
        return description
    return f'{filename}: {description}'


#: A would-be key candidate: leading indentation, then a non-empty run of
#: non-whitespace, non-colon characters, then ':' followed by whitespace or
#: end of line (Contract 03 §Hints (a)).
_WOULD_BE_KEY_RE = re.compile(r'^[ \t]*([^\s:]+):(?=[ \t]|$)')

#: The grammar's own key rule (§4.5, D20): exactly `[a-z][a-z0-9_-]*`.
_KEY_PATTERN = re.compile(r'[a-z][a-z0-9_-]*')


def would_be_key(line_text: str) -> str | None:
    """Return the `RUN` would-be-key candidate in `line_text`, or `None` if there isn't one.

    Matches `_WOULD_BE_KEY_RE` against `line_text` and returns the captured
    run only when it does NOT already fully match the grammar's key pattern
    (Contract 03 §Hints (a)) — a line that already lexes as a valid key never
    gets a "not a key" hint about itself.
    """
    match = _WOULD_BE_KEY_RE.match(line_text)
    if match is None:
        return None
    run = match.group(1)
    if _KEY_PATTERN.fullmatch(run) is not None:
        return None
    return run


def _columns_phrase(columns: Sequence[int]) -> str:
    """Render the sorted, distinct `columns` as 'column 0', 'columns 0 and 2', or 'columns 0, 2 and 4'."""
    cols = sorted(set(columns))
    if len(cols) == 1:
        return f'column {cols[0]}'
    *head, last = (str(c) for c in cols)
    return f"columns {', '.join(head)} and {last}"


def out_of_context_description(
    *,
    line_number: int,
    column: int,
    kind: str,
    open_columns: Sequence[int],
    other_kind: str | None,
    continues_at: int | None,
    list_under_key: bool,
    would_be_key_name: str | None,
) -> str:
    """Build `OutOfContextNodeError`'s description (Contract 03 §Messages).

    `other_kind` is `None` when `column` is not one of `open_columns` (form
    1: "does not fit any open block"); otherwise it is `'keys'` or `'list
    items'` (form 2: "is a {kind}, but the open block ... holds
    {other_kind}"). `continues_at`, when given, appends the text-value
    clause. `list_under_key` selects hint (b); otherwise `would_be_key_name`
    (already gated by the caller), when given, selects hint (a) — escaped
    through `_printable` so an unprintable would-be key does not leak raw
    control characters into `.message` (§Surface).
    """
    cols_phrase = _columns_phrase(open_columns)
    if other_kind is None:
        sentence = (
            f'Line {line_number}, at column {column}, does not fit any open block; open blocks are at {cols_phrase}.'
        )
    else:
        sentence = (
            f'Line {line_number}, at column {column}, is a {kind}, but the open block at column {column} '
            f'holds {other_kind}; open blocks are at {cols_phrase}.'
        )
    if continues_at is not None:
        sentence = f'{sentence[:-1]}; the open value continues at column {continues_at}.'
    hint: str | None = None
    if list_under_key:
        hint = "Hint: a list under a key must be indented past the key's column."
    elif would_be_key_name is not None:
        escaped = _printable(would_be_key_name)
        hint = f"Hint: '{escaped}' is not a key; a key is lowercase ASCII letters, digits, '-' and '_', starting with a letter."
    if hint is not None:
        sentence = f'{sentence} {hint}'
    return sentence


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
