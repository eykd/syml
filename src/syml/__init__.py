"""SYML (Simple YAML-like Markup Language) is a simple markup language with similar structure to YAML, but without all the gewgaws and folderol."""

import os
from typing import IO

from . import parsers
from .basetypes import StrPath, SymlData, SymlInput
from .exceptions import (
    DuplicateKeyError,
    EncodingError,
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
    if not isinstance(document, str):
        message = f'loads() expects str, not {type(document).__name__}'
        raise TypeError(message)
    return parsers.parse(document, filename=filename).as_data()


def load(file_obj: IO[str] | IO[bytes], filename: StrPath | None = None) -> SymlData:
    """Load a SYML document from a text or binary file-like object."""
    if filename is None:
        filename = _resolve_filename(file_obj)
    try:
        raw = file_obj.read()
    except UnicodeDecodeError as err:
        raise encoding_error(err, filename) from err
    except ValueError as err:
        message = f'load() could not read file_obj: {err}'
        raise TypeError(message) from err
    if isinstance(raw, bytes):
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError as err:
            raise encoding_error(err, filename) from err
    elif isinstance(raw, str):
        text = raw
    else:
        message = f'load() expects file_obj.read() to return str or bytes, not {type(raw).__name__}'
        raise TypeError(message)
    return loads(text, filename=filename)


def _resolve_filename(file_obj: IO[str] | IO[bytes]) -> StrPath | None:
    """Return `file_obj.name`, `os.fsdecode`d, when it is a usable path-like value, else `None`."""
    name = getattr(file_obj, 'name', None)
    if isinstance(name, str | os.PathLike):
        return os.fsdecode(name)
    return None


def parse(document: str, filename: StrPath | None = None) -> Root:
    """Parse a SYML document into its `Root` node (Contract 06 §`parse`)."""
    return parsers.parse(document, filename=filename)
