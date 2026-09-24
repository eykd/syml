"""SYML (Simple YAML-like Markup Language) is a simple markup language with similar structure to YAML, but without all the gewgaws and folderol."""

from pathlib import Path
from typing import IO

from . import parsers
from .basetypes import StrPath, SymlData, SymlInput
from .exceptions import (
    DuplicateKeyError,
    EncodingError,
    MalformedQuotedStringError,
    OutOfContextNodeError,
    ParseError,
    TabIndentationError,
    UnrepresentableValueError,
)
from .nodes import Root
from .preprocess import encoding_error
from .serializer import dump, dumps

__all__ = [
    'DuplicateKeyError',
    'EncodingError',
    'MalformedQuotedStringError',
    'OutOfContextNodeError',
    'ParseError',
    'Root',
    'SymlData',
    'SymlInput',
    'TabIndentationError',
    'UnrepresentableValueError',
    'dump',
    'dumps',
    'load',
    'loads',
    'parse',
]


def loads(document: str, filename: StrPath | None = None) -> SymlData:
    """Load a SYML document from a string."""
    return parsers.parse(document, filename=filename).as_data()


def load(file_obj: IO[str] | IO[bytes], filename: StrPath | None = None) -> SymlData:
    """Load a SYML document from a text or binary file-like object."""
    if filename is None:
        filename = _resolve_filename(file_obj)
    try:
        raw = file_obj.read()
        text = raw.decode('utf-8') if isinstance(raw, bytes) else raw
    except UnicodeDecodeError as err:
        raise encoding_error(err, filename) from err
    return loads(text, filename=filename)


def _resolve_filename(file_obj: IO[str] | IO[bytes]) -> StrPath | None:
    """Return `file_obj.name` when it is a usable path-like value, else `None`."""
    name = getattr(file_obj, 'name', None)
    return name if isinstance(name, str | Path) else None


def parse(document: str, filename: StrPath | None = None) -> Root:
    """Parse a SYML document into its `Root` node (Contract 06 §`parse`)."""
    return parsers.parse(document, filename=filename)
