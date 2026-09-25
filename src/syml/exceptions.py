"""Exceptions for parsing SYML documents"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

from .basetypes import KEY_PATTERN

if TYPE_CHECKING:  # pragma: nocover
    from collections.abc import Sequence

    from .basetypes import Pos, StrPath


def error_message(description: str, filename: StrPath | None) -> str:
    """`description` alone when filename is None, else f'{filename}: {description}'.

    `filename` is rendered through `_truncated_filename_window(filename)`
    before being interpolated, so a hostile multi-megabyte filename still
    yields a bounded result while its basename survives (Contract 03
    §Bounded rendering, D34, syml-cjk2.19) — refining syml-cjk2.5's original
    head-window treatment, which cut off the very basename a `path:line:col`
    reader needs.
    """
    if filename is None:
        return description
    return f'{_truncated_filename_window(os.fspath(filename))}: {description}'


#: A would-be key candidate: leading indentation, then a non-empty run of
#: non-whitespace, non-colon characters, then ':' followed by whitespace or
#: end of line (Contract 03 §Hints (a)).
_WOULD_BE_KEY_RE = re.compile(r'^[ \t]*([^\s:]+):(?=[ \t]|$)')


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
    if KEY_PATTERN.fullmatch(run) is not None:
        return None
    return run


#: Hint (c) candidates (Contract 03 §Hints (c), D26): a key immediately
#: followed by a non-space character after its colon, or a list marker
#: immediately followed by a non-space character. Both patterns are
#: prefixed with `[ \t]*` (matching `_WOULD_BE_KEY_RE`'s tolerance for
#: leading indentation) rather than D26's bare `^[a-z][a-z0-9_-]*:\S` /
#: `^-\S`, since the lines this hint fires on are always indented. The list
#: pattern excludes a second leading `-` (`--`, `---`) so this hint never
#: fires on a document-marker-shaped line; hint (e) owns that.
_MISSING_SPACE_KEY_RE = re.compile(r'^[ \t]*[a-z][a-z0-9_-]*:\S')
_MISSING_SPACE_LIST_RE = re.compile(r'^[ \t]*-(?!-)\S')


def needs_space_after_marker(line_text: str) -> bool:
    """Return whether `line_text` looks like a key or list marker missing its trailing space (Contract 03 §Hints (c))."""
    return _MISSING_SPACE_KEY_RE.match(line_text) is not None or _MISSING_SPACE_LIST_RE.match(line_text) is not None


#: Hint (d) candidate (Contract 03 §Hints (d), D27): a comment-shaped line
#: — after its indentation, `#` or `//` — reaching a raise site at all. A
#: column-0 comment never reaches here (the visitor drops it before the
#: builder sees it, D23); only an *indented* `#`/`//` line, which lexes as
#: text, can fail to incorporate and land here.
_COMMENT_SHAPED_RE = re.compile(r'^[ \t]*(#|//)')


def is_comment_shaped(line_text: str) -> bool:
    """Return whether `line_text`, after its indentation, starts with `#` or `//` (Contract 03 §Hints (d))."""
    return _COMMENT_SHAPED_RE.match(line_text) is not None


#: Hint (e) candidate (Contract 03 §Hints (e), D27): a line whose entire
#: content, after indentation and trailing whitespace, is exactly `---` or
#: `...` — a YAML document marker, which SYML has no equivalent of (D23).
_DOCUMENT_MARKER_RE = re.compile(r'^[ \t]*(---|\.\.\.)[ \t]*$')


def is_document_marker(line_text: str) -> bool:
    """Return whether `line_text`, after indentation, is exactly `---` or `...` (Contract 03 §Hints (e))."""
    return _DOCUMENT_MARKER_RE.match(line_text) is not None


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
    missing_space_after_marker: bool = False,
    comment_shaped: bool = False,
    document_marker: bool = False,
) -> str:
    """Build `OutOfContextNodeError`'s description (Contract 03 §Messages).

    `other_kind` is `None` when `column` is not one of `open_columns` (form
    1: "does not fit any open block"); otherwise it is `'keys'` or `'list
    items'` (form 2: "is a {kind}, but the open block ... holds
    {other_kind}"). `continues_at`, when given, appends the text-value
    clause. `list_under_key` selects hint (b); otherwise `would_be_key_name`
    (already gated by the caller), when given, selects hint (a) — escaped
    through `_printable` so an unprintable would-be key does not leak raw
    control characters into `.message` (§Surface); otherwise
    `missing_space_after_marker` (already gated by the caller, D26) selects
    hint (c); otherwise `comment_shaped` (D27) selects hint (d); otherwise
    `document_marker` (D27) selects hint (e). Hints (c), (d), and (e) have no
    interpolated content, so none needs `_printable`/`_truncated_window`
    bounding. The caller (`nodes._hint_candidates`) guarantees at most one of
    `would_be_key_name`/`missing_space_after_marker`/`comment_shaped`/
    `document_marker` is ever truthy at once, so this `elif` chain's order
    only documents precedence — it never has to arbitrate a real conflict.
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
        escaped = _printable(_truncated_window(would_be_key_name, center=0))
        hint = f"Hint: '{escaped}' is not a key; a key is lowercase ASCII letters, digits, '-' and '_', starting with a letter."
    elif missing_space_after_marker:
        hint = 'Hint: a key or list marker needs a space after it.'
    elif comment_shaped:
        hint = "Hint: comments must start at column 0; an indented '#' line is text."
    elif document_marker:
        hint = 'Hint: SYML has no document markers.'
    if hint is not None:
        sentence = f'{sentence} {hint}'
    return sentence


def duplicate_key_description(key: str, first_line: int) -> str:
    """Build `DuplicateKeyError`'s description: `Duplicate key '{key}' (first defined at line {N})`.

    `key` is rendered through `_truncated_window(key, center=0)` before being
    quoted, mirroring hint (a)'s treatment of a would-be key (Contract 03
    §Messages/§Bounded rendering, syml-s9p9.14): the grammar's key pattern
    (`[a-z][a-z0-9_-]*`) has no length bound, so an attacker-repeated 1 MB
    key would otherwise make `.message`/`str(e)` scale with the key's
    length. No `_printable` escaping is needed here — the key pattern admits
    no non-printable code point. The caller still stores the full,
    untruncated `key` on `DuplicateKeyError.key`/`.args`.

    `first_line` is the 1-indexed line the key's earlier, already-incorporated
    occurrence started on (`DuplicateKeyError.first_position.line`), so a
    reader of a long file can find both locations without re-scanning the
    document (D32, syml-cjk2.16).
    """
    return f"Duplicate key '{_truncated_window(key, center=0)}' (first defined at line {first_line})"


def _printable(text: str) -> str:
    """Replace every non-`str.isprintable()` character in `text` with its Python escape.

    Used to render `line_text` and `filename` in `ParseError.__str__` without
    echoing raw control characters, ANSI escapes, or lone surrogates onto the
    caller's terminal/stream (Contract 03 §Security).
    """
    return ''.join(ch if ch.isprintable() else repr(ch)[1:-1] for ch in text)


#: Window width (in code points of the *unescaped* input) rendered around a
#: point of interest by `_truncated_window` (Contract 03 §Surface/§Hints (a)).
_TRUNCATION_WINDOW = 80


def _truncated_window(text: str, *, center: int, width: int = _TRUNCATION_WINDOW) -> str:
    r"""Return a bounded slice of `text` around code-point index `center`, elided on any cut side.

    Bounds `_printable`'s escape expansion (each character can grow to
    several characters, e.g. `'\\x00'` is 4 characters) on attacker-controlled
    input by capping the window's *pre-escape* length, so the rendered output
    stays proportional to `width` regardless of `len(text)` — a single 1 MB
    hostile line no longer yields a multi-megabyte `.message`/`str(e)`
    (Contract 03 §Hints (a) / §Surface, syml-s9p9.9). `center` is clamped
    into range; an ellipsis marker (`'…'`) replaces each side that gets cut.
    """
    if len(text) <= width:
        return text
    half = width // 2
    start = max(0, min(center, len(text)) - half)
    end = min(len(text), start + width)
    start = max(0, end - width)
    prefix = '…' if start > 0 else ''
    suffix = '…' if end < len(text) else ''
    return f'{prefix}{text[start:end]}{suffix}'


#: Window width (in code points) a filename is allowed to pass through
#: whole before `_truncated_filename_window` starts eliding its head
#: (Contract 03 §Bounded rendering, D34, syml-cjk2.19).
_FILENAME_WINDOW = 1024


def _truncated_filename_window(text: str, *, width: int = _FILENAME_WINDOW) -> str:
    """Return `text` unchanged if `len(text) <= width`, else `'…' + text[-(width - 1):]`.

    Unlike `_truncated_window` (which centers its window and can elide
    either side), a filename is always windowed from the **tail**: the
    basename — the part a `path:line:col` reader actually needs — sits at
    the end of a path, so eliding the head instead of the middle or tail
    keeps it intact regardless of how long the filename's leading
    directories are (D34, syml-cjk2.19; refines syml-cjk2.5's original
    `_truncated_window(filename, center=0)` head-keeping treatment, which
    cut the basename off any path longer than 80 code points).
    """
    if len(text) <= width:
        return text
    return f'…{text[-(width - 1) :]}'


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
        bom_offset: int = 0,
    ) -> None:
        """Store `message`, `position`, and `line_text`, preserving `.args`.

        `message` is the bare description (no filename prefix). `filename`,
        when given, is normalized with `os.fspath` (`''` normalizes to
        `None`) and used both to build the prefixed `.message` and to render
        `__str__`'s `<filename>:` segment.

        `bom_offset` is private (not stored as a public attribute; it isn't
        part of Contract 05 §Surface's `message`/`position`/`line_text`
        contract). `line_text` reflects the §9.0-normalized (BOM-stripped)
        line for every error raised after preprocessing, while `position`
        keeps the caller's original-text coordinates (FR-013), so on line 1
        of a BOM-led document `position.column` counts the stripped BOM and
        is one greater than its index into `line_text` (D33, syml-cjk2.17).
        `bom_offset` — 1 on such a line, 0 everywhere else — lets `__str__`
        centre its excerpt window on the right `line_text` index without
        moving `position` itself. `EncodingError` is raised before step 1
        of preprocessing (§9.0) and its `line_text` is the replace-decoded
        raw prefix, BOM included literally, so it never needs this offset.
        """
        normalized_filename = os.fspath(filename) if filename else None
        full_message = error_message(message, normalized_filename)
        super().__init__(full_message, position, line_text, *extra)
        self.message = full_message
        self.position = position
        self.line_text = line_text
        self._description = message
        self._filename = normalized_filename
        self._bom_offset = bom_offset

    def __str__(self) -> str:
        r"""Render `<filename>:<line>:<column>: <description>\n<line_text>` (Contract 03 §Surface).

        `<filename>:` is omitted when no filename is known. `<line>` is
        1-indexed, `<column>` 0-indexed, both taken from `self.position`
        (§10.2). The filename and line text are rendered through
        `_printable` so no non-printable character (including a stray
        newline in a caller-supplied filename) escapes into the two-line
        shape this format promises. The filename is first windowed through
        `_truncated_filename_window(self._filename)` — which keeps the
        filename's tail so its basename survives (D34, syml-cjk2.19) — and
        the line text through `_truncated_window(self.line_text, center=self.position.column - self._bom_offset)`
        — `self._bom_offset` re-anchors the window's center onto
        `self.line_text`'s own index space, since `self.position.column`
        counts a BOM-stripped-before-`line_text` BOM on line 1 (D33,
        syml-cjk2.17) — so a hostile multi-megabyte filename or `line_text`
        (both unbounded, per `.line_text`'s own attribute contract, and
        `filename` normally being caller-controlled) still yields a bounded
        `str(e)` (Contract 03 §Surface, syml-s9p9.9, syml-cjk2.5, D34);
        `self.line_text` itself is untouched.
        """
        prefix = f'{_printable(_truncated_filename_window(self._filename))}:' if self._filename else ''
        windowed_line_text = _truncated_window(self.line_text, center=self.position.column - self._bom_offset)
        return f'{prefix}{self.position.line}:{self.position.column}: {self._description}\n{_printable(windowed_line_text)}'


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
        bom_offset: int = 0,
    ) -> None:
        """Store the repeated key and the position of its first occurrence."""
        super().__init__(message, position, line_text, key, first_position, filename=filename, bom_offset=bom_offset)
        self.key = key
        self.first_position = first_position


#: Max number of subscript segments `format_data_path` renders before eliding
#: the middle with a single `'…'` (Contract 04 §Error text and the data
#: path, D30, syml-cjk2.18). Split evenly between the path's head and tail.
_MAX_PATH_SEGMENTS = 6


def format_data_path(path: Sequence[str | int]) -> str:
    """Render `path` as a trailing ' at [...][...]' clause, or '' when `path` is empty (D30).

    `path` is a sequence of mapping keys (`str`) and list indexes (`int`)
    tracing a value from the root of a `dumps` call, in Python subscript
    form, e.g. `['a']['b'][1]`. Shared by `UnrepresentableValueError` and
    the `dumps` `TypeError` so both render the same path shape.

    Bounded (D30, syml-cjk2.18): a `str` segment is windowed through
    `_truncated_window(key, center=0)` before `repr`, the same treatment
    `DuplicateKeyError` and hint (a) give a hostile key (Contract 03
    §Bounded rendering), so an attacker-controlled key of any length still
    yields a bounded segment. Depth is bounded too: only the first and last
    `_MAX_PATH_SEGMENTS // 2` rendered segments are kept, with a single
    `'…'` standing in for everything elided between them, so the clause
    cannot grow with the path's depth. This only bounds the rendered
    clause — the caller's `path` (and `UnrepresentableValueError.path`)
    stays the full, untruncated tuple.
    """
    if not path:
        return ''
    segments = [f'[{_truncated_window(key, center=0)!r}]' if isinstance(key, str) else f'[{key!r}]' for key in path]
    if len(segments) > _MAX_PATH_SEGMENTS:
        half = _MAX_PATH_SEGMENTS // 2
        segments = [*segments[:half], '…', *segments[-half:]]
    return ' at ' + ''.join(segments)


class UnrepresentableValueError(ValueError):
    """A value has no SYML encoding (§11.2.1-.3). Raised by `dumps`, not a `ParseError`.

    `.path` is a tuple of mapping keys (`str`) and list indexes (`int`)
    tracing the offending value from the root of the `dumps` call; `()` for
    a root value. `str(e)` is `message` alone (D30) — never the tuple
    `args` would otherwise render — with `.path` appended as a Python
    subscript clause, e.g. `... at ['a']['b'][1]`; a root value's message
    carries no path clause.
    """

    def __init__(self, message: str, path: tuple[str | int, ...] = ()) -> None:
        """Store `.message` (with `path`'s clause appended) and `.path` itself."""
        full_message = f'{message}{format_data_path(path)}'
        super().__init__(full_message)
        self.message = full_message
        self.path = path

    def __str__(self) -> str:
        """Render `.message` alone (D30), not a tuple repr of `.args`."""
        return self.message
