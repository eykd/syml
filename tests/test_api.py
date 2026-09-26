"""Tests for the `loads`/`load` end-to-end entry points (src/syml/__init__.py, Contract 06)."""

from __future__ import annotations

import io
import os
import pathlib

import pytest

import syml
from syml import basetypes, serializer
from syml.exceptions import DuplicateKeyError, EncodingError, ParseError


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

    def test_load_from_a_charmap_text_stream_names_its_own_codec_not_charmap(self) -> None:
        """A charmap-based codec (e.g. `cp1252`) is named by its own `encoding`, not `'charmap'`.

        Every charmap-based codec (`cp1252`, `cp437`, the `latin-*` family, ...)
        raises `UnicodeDecodeError` with `err.encoding == 'charmap'`, so `load`
        must prefer the stream's own `encoding` attribute over `err.encoding`
        when naming the codec (Contract 03 §`EncodingError`).
        """
        handle = io.TextIOWrapper(io.BytesIO(b'a: \x81'), encoding='cp1252')

        with pytest.raises(EncodingError) as exc_info:
            syml.load(handle)

        assert exc_info.value.message == 'Invalid cp1252 (byte 0x81)'

    def test_load_from_a_utf8_sig_text_stream_keeps_the_d31_utf8_text(self) -> None:
        """A `utf-8-sig` stream is still UTF-8 (D31), refined `syml-cjk2.28`.

        `utf-8-sig` is a member of the UTF-8 family (it only adds BOM
        handling), so an invalid-byte failure on such a stream must keep
        the "save the file as UTF-8" advice, not name `utf-8-sig` as if it
        were an unrelated codec.
        """
        handle = io.TextIOWrapper(io.BytesIO(b'a: \xe9'), encoding='utf-8-sig')

        with pytest.raises(EncodingError) as exc_info:
            syml.load(handle)

        assert exc_info.value.message == 'Invalid UTF-8 (byte 0xe9); save the file as UTF-8'

    def test_load_falls_back_to_err_encoding_when_stream_encoding_name_is_unknown(self) -> None:
        """A stream `.encoding` naming an unknown codec falls back to `err.encoding`, `syml-cjk2.28`.

        Before this fix, `codecs.lookup('no-such-codec')` raised `LookupError`
        directly out of `encoding_error`, so a bogus stream `.encoding` leaked
        a builtin `LookupError` instead of `EncodingError`.
        """

        class _BogusEncodingHandle:
            encoding = 'no-such-codec'

            def read(self) -> str:
                raise UnicodeDecodeError('utf-8', b'\xe9', 0, 1, 'bad byte')

        with pytest.raises(EncodingError) as exc_info:
            syml.load(_BogusEncodingHandle())  # type: ignore[arg-type]

        assert exc_info.value.message == 'Invalid UTF-8 (byte 0xe9); save the file as UTF-8'

    def test_load_falls_back_to_err_encoding_when_stream_encoding_is_not_a_str(self) -> None:
        """A non-`str` stream `.encoding` falls back to `err.encoding`, `syml-cjk2.28`.

        Before this fix, `codecs.lookup(42)` raised `TypeError` directly out
        of `encoding_error`, so a non-`str` stream `.encoding` leaked a
        builtin `TypeError` instead of `EncodingError`.
        """

        class _NonStrEncodingHandle:
            encoding = 42

            def read(self) -> str:
                raise UnicodeDecodeError('utf-8', b'\xe9', 0, 1, 'bad byte')

        with pytest.raises(EncodingError) as exc_info:
            syml.load(_NonStrEncodingHandle())  # type: ignore[arg-type]

        assert exc_info.value.message == 'Invalid UTF-8 (byte 0xe9); save the file as UTF-8'


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


class TestLoadsRejectsNonStrInputWithAClearTypeError:
    """Contract 05 §Behaviour: non-`str` input to `loads` raises `TypeError` naming the type."""

    @pytest.mark.parametrize(
        ('document', 'expected_type_name'),
        [
            pytest.param(b'k: v', 'bytes', id='bytes'),
            pytest.param(None, 'NoneType', id='none'),
            pytest.param(1, 'int', id='int'),
        ],
    )
    def test_loads_raises_a_type_error_naming_the_received_type(
        self,
        document: object,
        expected_type_name: str,
    ) -> None:
        with pytest.raises(TypeError) as exc_info:
            syml.loads(document)  # type: ignore[arg-type]

        assert expected_type_name in str(exc_info.value)


class TestLoadRejectsNonTextNonBytesReadResults:
    """Contract 05 §Behaviour: `load()` on a non-`str`/`bytes` `read()` result raises `TypeError`."""

    def test_a_memoryview_read_result_raises_a_type_error_naming_memoryview(self) -> None:
        class _MemoryviewHandle:
            def read(self) -> memoryview:
                return memoryview(b'k: v')

        with pytest.raises(TypeError, match='memoryview'):
            syml.load(_MemoryviewHandle())  # type: ignore[arg-type]


class TestLoadOnANonFileObjectRaisesTypeError:
    """Contract 05 §Behaviour: `load()` on a non-file object raises `TypeError`, not `AttributeError`."""

    def test_load_none_raises_type_error_naming_nonetype(self) -> None:
        with pytest.raises(TypeError, match='NoneType'):
            syml.load(None)  # type: ignore[arg-type]

    def test_load_a_str_raises_type_error_naming_str(self) -> None:
        with pytest.raises(TypeError, match='str'):
            syml.load('some str')  # type: ignore[arg-type]

    def test_load_an_object_with_only_readline_raises_type_error(self) -> None:
        class _ReadlineOnlyHandle:
            def readline(self) -> str:
                return 'k: v'

        with pytest.raises(TypeError, match='_ReadlineOnlyHandle'):
            syml.load(_ReadlineOnlyHandle())  # type: ignore[arg-type]


class TestLoadOnAClosedHandleRaisesTypeError:
    """Contract 05 §Behaviour: `load()` on a closed handle raises a chained `TypeError`, not `ValueError`."""

    def test_a_closed_string_io_handle_raises_type_error_chained_from_value_error(self) -> None:
        handle = io.StringIO('key: value')
        handle.close()

        with pytest.raises(TypeError) as exc_info:
            syml.load(handle)

        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_a_closed_handle_is_not_caught_by_except_parse_error(self) -> None:
        """`except ParseError` must not confuse the closed-handle error for a parse error."""
        handle = io.StringIO('key: value')
        handle.close()

        try:
            syml.load(handle)
        except ParseError:
            pytest.fail('closed-handle TypeError was caught by except ParseError')
        except TypeError:
            pass
        else:
            pytest.fail('expected load() to raise TypeError on a closed handle')


class TestLoadHonoursAnyOsPathLikeFilename:
    """Contract 05 §Behaviour: `load()` honours any `os.PathLike` `.name`, not just `str`/`Path`."""

    def test_a_pathlib_pure_posix_path_name_prefixes_the_message(self) -> None:
        handle = io.StringIO('key: value1\nkey: value2')
        handle.name = pathlib.PurePosixPath('p.syml')

        with pytest.raises(DuplicateKeyError) as exc_info:
            syml.load(handle)

        assert exc_info.value.message.startswith('p.syml: ')

    def test_a_custom_os_pathlike_name_is_honoured_via_fspath(self) -> None:
        class _CustomPath(os.PathLike[str]):
            def __fspath__(self) -> str:
                return 'custom.syml'

        handle = io.StringIO('key: value1\nkey: value2')
        handle.name = _CustomPath()

        with pytest.raises(DuplicateKeyError) as exc_info:
            syml.load(handle)

        assert exc_info.value.message.startswith('custom.syml: ')

    def test_a_surrogate_escaped_pathlike_name_is_fsdecoded_raw_and_printable_escaped_in_str(self) -> None:
        handle = io.StringIO('key: value1\nkey: value2')
        handle.name = pathlib.PurePosixPath(os.fsdecode(b'\xff.syml'))

        with pytest.raises(DuplicateKeyError) as exc_info:
            syml.load(handle)

        assert exc_info.value.message.startswith('\udcff.syml: ')
        assert str(exc_info.value).startswith('\\udcff.syml:')
        str(exc_info.value).encode('utf-8')

    def test_an_int_name_yields_no_filename(self) -> None:
        handle = io.StringIO('key: value1\nkey: value2')
        handle.name = 5

        with pytest.raises(DuplicateKeyError) as exc_info:
            syml.load(handle)

        assert exc_info.value.message == "Duplicate key 'key' (first defined at line 1)"

    def test_a_bytes_name_yields_no_filename(self) -> None:
        handle = io.StringIO('key: value1\nkey: value2')
        handle.name = b'x.syml'

        with pytest.raises(DuplicateKeyError) as exc_info:
            syml.load(handle)

        assert exc_info.value.message == "Duplicate key 'key' (first defined at line 1)"


class TestParseIsAPublicExport:
    """Contract 06 §`parse`: promoted from `syml.parsers.parse` to `syml.parse` (US5)."""

    def test_parse_returns_a_root_node_whose_as_data_matches_loads(self) -> None:
        """`syml.parse` returns a `Root` node; `.as_data()` equals `syml.loads` on the same document."""
        root = syml.parse('key: value')

        assert isinstance(root, syml.Root)
        assert root.as_data() == syml.loads('key: value')


class TestDumpsDumpSymlDataSymlInputArePublicExports:
    """Contract 09 FR-015 (CHANGELOG.md items 12/14): `dumps`/`dump`/`SymlData`/`SymlInput` are public exports."""

    def test_dumps_is_importable_from_the_syml_package_and_matches_the_serializer(self) -> None:
        """`syml.dumps` is the same callable as `syml.serializer.dumps`."""
        assert syml.dumps is serializer.dumps

    def test_dump_is_importable_from_the_syml_package_and_matches_the_serializer(self) -> None:
        """`syml.dump` is the same callable as `syml.serializer.dump`."""
        assert syml.dump is serializer.dump

    def test_symldata_is_importable_from_the_syml_package(self) -> None:
        """`syml.SymlData` is the same type alias as `syml.basetypes.SymlData`."""
        assert syml.SymlData is basetypes.SymlData

    def test_symlinput_is_importable_from_the_syml_package(self) -> None:
        """`syml.SymlInput` is the same type alias as `syml.basetypes.SymlInput`."""
        assert syml.SymlInput is basetypes.SymlInput
