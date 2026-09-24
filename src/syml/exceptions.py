"""Exceptions for parsing SYML documents"""


class ParseError(ValueError):
    """An error encountered while parsing"""


class OutOfContextNodeError(ParseError):
    """A node encountered in an illegal context"""


class TabIndentationError(ParseError):
    """A tab character was found in a line's leading whitespace (§9.0.3)."""
