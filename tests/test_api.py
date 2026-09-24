"""Tests for the `loads` end-to-end entry point (src/syml/__init__.py, Contract 06)."""

from __future__ import annotations

import pytest

import syml
from syml.exceptions import DuplicateKeyError


class TestLoadsCarriesFilenameIntoEveryParseErrorMessage:
    """Contract 05 §`message carries the filename`; Contract 06 §`loads`.

    Every raise site reached while walking the parsed tree — not just the
    lexing/preprocessing raise sites — must format its message through
    `error_message(description, filename)` so a caller who passed
    `filename=` to `loads` sees it in `str(exc)` / `exc.message`, no matter
    which stage of the pipeline raised.
    """

    def test_a_duplicate_key_error_from_loads_includes_the_given_filename(self) -> None:
        """A `DuplicateKeyError` raised while incorporating nodes still carries `filename`."""
        with pytest.raises(DuplicateKeyError) as exc_info:
            syml.loads('key: value1\nkey: value2', filename='example.syml')

        assert 'example.syml' in exc_info.value.message
