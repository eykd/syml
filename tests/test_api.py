"""Tests for the `loads`/`load` end-to-end entry points (src/syml/__init__.py, Contract 06)."""

from __future__ import annotations

import io

import pytest

import syml
from syml.exceptions import DuplicateKeyError, EncodingError


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


class TestLoadAcceptsTextAndBinaryStreams:
    """Contract 06 §`load`: `IO[str] | IO[bytes]`, `EncodingError` on invalid UTF-8 (US5.5, US5.6)."""

    def test_load_from_a_binary_stream_with_valid_utf8_matches_a_text_stream(self) -> None:
        """`load` on a `BytesIO` of valid UTF-8 yields the same result as `load` on a `StringIO`."""
        text_result = syml.load(io.StringIO('key: value'))
        binary_result = syml.load(io.BytesIO(b'key: value'))

        assert binary_result == text_result

    def test_load_from_a_binary_stream_with_invalid_utf8_raises_encoding_error(self) -> None:
        """`load` on a `BytesIO` carrying invalid UTF-8 bytes raises `EncodingError`, not `UnicodeDecodeError`."""
        with pytest.raises(EncodingError):
            syml.load(io.BytesIO(b'key: \xff\xfe'))

    def test_load_from_a_text_stream_with_invalid_bytes_raises_encoding_error(self) -> None:
        """A text handle that raises `UnicodeDecodeError` from `read()` is wrapped into `EncodingError`.

        Contract 06 §`load`: `read()` is wrapped in a `try`/`except UnicodeDecodeError`,
        because a text handle decodes inside `read()` itself, so an unwrapped `load`
        would let a non-`ParseError` `UnicodeDecodeError` escape (forbidden by FR-009).
        """
        handle = io.TextIOWrapper(io.BytesIO(b'key: \xff\xfe'), encoding='utf-8')

        with pytest.raises(EncodingError):
            syml.load(handle)


class TestLoadResolvesFilenameFromFileObj:
    """Contract 06 §`load`: `filename` defaults to `file_obj.name`; an explicit `filename` wins."""

    def test_an_explicit_filename_argument_wins_over_file_obj_name(self) -> None:
        """`load(file_obj, filename='given.syml')` uses the given name, not `file_obj.name`."""
        handle = io.StringIO('key: value1\nkey: value2')
        handle.name = 'ignored.syml'

        with pytest.raises(DuplicateKeyError) as exc_info:
            syml.load(handle, filename='given.syml')

        assert 'given.syml' in exc_info.value.message
        assert 'ignored.syml' not in exc_info.value.message


class TestParseIsAPublicExport:
    """Contract 06 §`parse`: promoted from `syml.parsers.parse` to `syml.parse` (US5)."""

    def test_parse_returns_a_root_node_whose_as_data_matches_loads(self) -> None:
        """`syml.parse` returns a `Root` node; `.as_data()` equals `syml.loads` on the same document."""
        root = syml.parse('key: value')

        assert isinstance(root, syml.Root)
        assert root.as_data() == syml.loads('key: value')
