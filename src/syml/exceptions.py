"""Exceptions for parsing SYML documents"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: nocover
    from .basetypes import Pos


class ParseError(ValueError):
    """An error encountered while parsing"""


class OutOfContextNodeError(ParseError):
    """A node encountered in an illegal context"""


class TabIndentationError(ParseError):
    """A tab character was found in a line's leading whitespace (§9.0.3)."""


class DuplicateKeyError(ParseError):
    """A mapping key repeats an earlier sibling's key at the same level (FR-007, §8.3)."""

    def __init__(self, *args: object, key: str, first_position: Pos) -> None:
        """Store the repeated key and the position of its first occurrence."""
        super().__init__(*args)
        self.key = key
        self.first_position = first_position
