"""SYML (Simple YAML-like Markup Language) is a simple markup language with similar structure to YAML, but without all the gewgaws and folderol."""

from pathlib import Path
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
from .nodes import Root
from .preprocess import encoding_error

__all__ = [
    'DuplicateKeyError',
    'EncodingError',
    'MalformedQuotedStringError',
    'OutOfContextNodeError',
    'ParseError',
    'Root',
    'TabIndentationError',
    'UnrepresentableValueError',
    'load',
    'loads',
    'parse',
]


def loads(document: str, filename: StrPath | None = None) -> list[Any] | dict[str, Any] | str:
    """Load a SYML document from a string."""
    return parsers.parse(document, filename=filename).as_data()


def load(file_obj: IO[str] | IO[bytes], filename: StrPath | None = None) -> list[Any] | dict[str, Any] | str:
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


# Contract 09 FR-015 (CHANGELOG.md items 12/14): `dumps`/`dump`/`SymlData`/`SymlInput`
# are promoted to public exports of the `syml` package, mirroring `parse`. These are
# RED-phase stubs (syml-x0m.5.8.32) — the Green task (syml-x0m.5.8.33) replaces them
# with the real `syml.serializer`/`syml.basetypes` objects and adds them to `__all__`.
type SymlData = str | list[SymlData] | dict[str, SymlData]
SymlInput = str | list[Any] | dict[str, Any]


def dumps(data: SymlInput) -> str:
    """Serialize `data` to SYML text (stub — not yet wired to `syml.serializer.dumps`)."""
    raise NotImplementedError


def dump(data: SymlInput, file_obj: IO[str]) -> None:
    """Serialize `data` to SYML text, written to `file_obj` (stub — not yet wired to `syml.serializer.dump`)."""
    raise NotImplementedError
