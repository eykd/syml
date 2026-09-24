"""Utility functions for SYML"""

from functools import cache


@cache
def split_lines(text: str, keepends: bool = False) -> list[str]:  # noqa: FBT001, FBT002
    """Memoized version of str.splitlines()"""
    return text.splitlines(keepends=keepends)


def get_line(text: str, line_number: int) -> str:
    """Return the contents of the specified line number from the given text."""
    try:
        return split_lines(text, keepends=True)[line_number - 1]
    except IndexError:
        return ''


def get_line_text(text: str, line_number: int) -> str:
    """Return `get_line`'s result with any trailing line terminator stripped.

    This is what every `ParseError.line_text` (Contract 05 §`line_text`)
    should carry: the offending line's full original text, terminator
    excluded.
    """
    return get_line(text, line_number).rstrip('\r\n')
