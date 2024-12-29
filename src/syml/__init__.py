"""SYML (Simple YAML-like Markup Language) is a simple markup language with similar structure to YAML, but without all the gewgaws and folderol."""

from io import TextIOBase
from typing import Any

from . import parsers


def loads(document: str, **kwargs: Any) -> Any:  # noqa: ANN401
    """Load a SYML document from a string."""
    return parsers.parse(document, **kwargs)


def load(file_obj: TextIOBase, **kwargs: Any) -> Any:  # noqa: ANN401
    """Load a SYML document from a file-like object."""
    return loads(file_obj.read(), **kwargs)
