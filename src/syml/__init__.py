"""SYML (Simple YAML-like Markup Language) is a simple markup language with similar structure to YAML, but without all the gewgaws and folderol."""

from typing import IO, Any

from . import parsers
from .basetypes import StrPath
from .exceptions import (
    DuplicateKeyError,
    EncodingError,
    MalformedQuotedStringError,
    OutOfContextNodeError,
    ParseError,
    TabIndentationError,
    UnrepresentableValueError,
)
from .preprocess import encoding_error

__all__ = [
    'DuplicateKeyError',
    'EncodingError',
    'MalformedQuotedStringError',
    'OutOfContextNodeError',
    'ParseError',
    'TabIndentationError',
    'UnrepresentableValueError',
    'load',
    'loads',
]


def loads(document: str, filename: StrPath | None = None) -> list[Any] | dict[str, Any] | str:
    """Load a SYML document from a string."""
    return parsers.parse(document, filename=filename).as_data()


def load(file_obj: IO[str] | IO[bytes], filename: StrPath | None = None) -> list[Any] | dict[str, Any] | str:
    """Load a SYML document from a text or binary file-like object."""
    raw = file_obj.read()
    if isinstance(raw, bytes):
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError as err:
            raise encoding_error(err, filename) from err
    else:
        text = raw
    return loads(text, filename=filename)
