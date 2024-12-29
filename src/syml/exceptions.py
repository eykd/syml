"""Exceptions for parsing SYML documents"""


class ParseError(ValueError):
    """An error encountered while parsing"""


class OutOfContextNodeError(ParseError):
    """A node encountered in an illegal context"""
