"""SYML (Simple YAML-like Markup Language) is a simple markup language with similar structure to YAML, but without all the gewgaws and folderol."""

from io import TextIOBase
from typing import Any

from . import parsers
from .basetypes import StrPath


def loads(document: str, filename: StrPath | None = None) -> list[Any] | dict[str, Any] | str:
    """Load a SYML document from a string."""
    return parsers.parse(document, filename=filename).as_data()


def load(file_obj: TextIOBase, filename: StrPath | None = None) -> list[Any] | dict[str, Any] | str:
    """Load a SYML document from a file-like object."""
    return loads(file_obj.read(), filename=filename)
