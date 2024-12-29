"""Utility functions for SYML"""

from funcy import memoize


@memoize
def split_lines(text: str, keepends: bool = False) -> list[str]:  # noqa: FBT001, FBT002
    """Memoized version of str.splitlines()"""
    return text.splitlines(keepends=keepends)


def get_line(text: str, line_number: int) -> str:
    """Return the contents of the specified line number from the given text."""
    try:
        return split_lines(text, keepends=True)[line_number - 1]
    except IndexError:
        return ''
