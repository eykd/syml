"""Tests for src/syml/exceptions.py."""

from __future__ import annotations

import pathlib
import pickle  # noqa: S403 - test-only, deserializes only what this test just pickled

import pytest

import syml
from syml.basetypes import Pos
from syml.exceptions import DuplicateKeyError, OutOfContextNodeError, ParseError, error_message
from syml.preprocess import encoding_error


class TestLineTextIsTheOffendingLineOnEveryParseError:
    """Contract 05 §`line_text`.

    ``line_text`` is the original physical line containing ``position``,
    without its terminator — the *full* source line, not a truncated node
    span and not the line with its trailing newline still attached. Every
    raise site reached from a parsed document must honor this, not just the
    last line of a document.
    """

    @pytest.mark.parametrize(
        ('document', 'error_type', 'expected_line_text'),
        [
            pytest.param(
                'k: a\n    b\n  c\n',
                OutOfContextNodeError,
                '  c',
                id='out_of_context_node_error_strips_terminator',
            ),
            pytest.param(
                'a: 1\nb: 2\nb: 3\n',
                DuplicateKeyError,
                'b: 3',
                id='duplicate_key_error_is_the_full_line_not_the_key_span',
            ),
        ],
    )
    def test_line_text_is_the_full_offending_source_line(
        self,
        document: str,
        error_type: type[ParseError],
        expected_line_text: str,
    ) -> None:
        """`.line_text` equals the offending line's full original text, terminator excluded."""
        with pytest.raises(error_type) as exc_info:
            syml.loads(document)

        assert exc_info.value.line_text == expected_line_text


class TestParseErrorAttributeContract:
    """Contract 05 §Attribute contract (R-03).

    `ParseError.__init__` takes `message`, `position`, `line_text` and stores
    them as named attributes, while still preserving `.args` for existing
    `except ParseError as e: e.args[1]`-style code.
    """

    def test_parse_error_stores_message_position_and_line_text(self) -> None:
        """The three named attributes carry exactly the constructor arguments."""
        position = Pos(index=3, line=1, column=3)

        error = ParseError('Failed to incorporate a node', position, 'foo')

        assert error.message == 'Failed to incorporate a node'
        assert error.position == position
        assert error.line_text == 'foo'


class TestEncodingErrorPositionDerivation:
    """Contract 05 §`EncodingError` position derivation (R-04).

    `UnicodeDecodeError.start` is a byte offset, not a code-point index;
    `encoding_error` must convert it to original-text `Pos` coordinates.
    """

    def test_encoding_error_converts_byte_offset_to_code_point_position(self) -> None:
        """Assert converted `Pos` and `line_text` derived from a byte offset.

        A multi-byte char and a CRLF before the bad byte make byte- and
        code-point-counting diverge, so a naive `Pos(err.start, ...)`
        implementation cannot pass this test.
        """
        raw = b'k\xc3\xa9: v\r\nx: \xff'
        with pytest.raises(UnicodeDecodeError) as exc_info:
            raw.decode('utf-8')
        err = exc_info.value

        result = encoding_error(err, None)

        assert result.position == Pos(index=10, line=2, column=3)
        assert result.line_text == 'x: '
        assert result.message == 'Invalid encoding'


class TestWhichErrorForWhichConditionMapping:
    """Contract 05 §Which error for which condition.

    Every class in the mapping table must be reachable through the public
    `syml` package, not just `syml.exceptions` — a caller who wants to catch
    "the error for condition X" per the table needs `syml.<ClassName>` to
    exist.
    """

    @pytest.mark.parametrize(
        'class_name',
        [
            'OutOfContextNodeError',  # indentation/context violation (§8.1, §8.2)
            'DuplicateKeyError',  # key repeated within one mapping (§8.3)
            'TabIndentationError',  # tab in leading whitespace (§8.4, §9.0.3)
            'EncodingError',  # undecodable bytes from load (§11.1)
            'UnrepresentableValueError',  # value with no SYML encoding (§11.2.2-.4)
        ],
    )
    def test_every_mapped_error_class_is_exported_from_the_top_level_syml_package(
        self,
        class_name: str,
    ) -> None:
        """Every condition's mapped class is importable as `syml.<ClassName>`."""
        assert hasattr(syml, class_name), f'syml.{class_name} is not exported'


class TestErrorMessage:
    """Contract 05 §Surface: `error_message` carries the filename (red-team pass 14)."""

    def test_error_message_omits_filename_when_none(self) -> None:
        """`description` alone when `filename` is `None`."""
        assert error_message('Invalid encoding', None) == 'Invalid encoding'

    def test_error_message_prefixes_filename_when_given(self) -> None:
        """`f'{filename}: {description}'` when `filename` is given."""
        assert error_message('Invalid encoding', 'doc.syml') == 'doc.syml: Invalid encoding'


class TestParseErrorFilenameNormalization:
    """Contract 03 §Surface: `filename` is normalized with `os.fspath`; `''` behaves as `None`."""

    def test_no_filename_leaves_message_unprefixed(self) -> None:
        """`message` stays the bare description when no filename is given."""
        error = ParseError('Invalid encoding', Pos(0, 1, 0), '')

        assert error.message == 'Invalid encoding'

    def test_empty_string_filename_behaves_as_no_filename(self) -> None:
        """`filename=''` normalizes to `None`, so `.message` stays unprefixed."""
        error = ParseError('Invalid encoding', Pos(0, 1, 0), '', filename='')

        assert error.message == 'Invalid encoding'
        assert str(error).startswith('1:0: ')

    def test_string_filename_prefixes_message(self) -> None:
        """A plain `str` filename prefixes `.message` via `error_message`."""
        error = ParseError('Invalid encoding', Pos(0, 1, 0), '', filename='doc.syml')

        assert error.message == 'doc.syml: Invalid encoding'

    def test_pathlike_filename_is_normalized_with_fspath(self) -> None:
        """A `pathlib.Path` filename is normalized to its `str` form via `os.fspath`."""
        error = ParseError('Invalid encoding', Pos(0, 1, 0), '', filename=pathlib.Path('p.syml'))

        assert error.message == 'p.syml: Invalid encoding'
        assert str(error).startswith('p.syml:1:0: ')


class TestParseErrorStr:
    r"""Contract 03 §Surface: `__str__` is `<filename>:<line>:<column>: <description>\n<line_text>`."""

    def test_str_without_filename_omits_the_filename_segment(self) -> None:
        """No `<filename>:` segment appears when no filename is known."""
        error = ParseError('does not fit any open block', Pos(9, 3, 1), ' b: 2')

        assert str(error) == '3:1: does not fit any open block\n b: 2'

    def test_str_with_filename_prefixes_the_filename_segment(self) -> None:
        """`<filename>:` precedes `<line>:<column>:` when a filename is known."""
        error = ParseError('does not fit any open block', Pos(9, 3, 1), ' b: 2', filename='f.syml')

        assert str(error) == 'f.syml:3:1: does not fit any open block\n b: 2'
        assert error.message == 'f.syml: does not fit any open block'

    def test_str_renders_for_parse_error_with_and_without_a_filename(self) -> None:
        """`ParseError` itself renders the two-line `__str__` shape."""
        without_filename = ParseError('boom', Pos(1, 1, 1), 'x')
        with_filename = ParseError('boom', Pos(1, 1, 1), 'x', filename='f.syml')

        assert str(without_filename) == '1:1: boom\nx'
        assert str(with_filename) == 'f.syml:1:1: boom\nx'

    def test_str_renders_for_out_of_context_node_error_with_and_without_a_filename(self) -> None:
        """`OutOfContextNodeError` renders the same two-line `__str__` shape."""
        without_filename = OutOfContextNodeError('boom', Pos(1, 1, 1), 'x')
        with_filename = OutOfContextNodeError('boom', Pos(1, 1, 1), 'x', filename='f.syml')

        assert str(without_filename) == '1:1: boom\nx'
        assert str(with_filename) == 'f.syml:1:1: boom\nx'

    def test_str_renders_for_duplicate_key_error_with_and_without_a_filename(self) -> None:
        """`DuplicateKeyError` renders the same two-line `__str__` shape."""
        without_filename = DuplicateKeyError('boom', Pos(1, 1, 1), 'x', key='a', first_position=Pos(0, 1, 0))
        with_filename = DuplicateKeyError(
            'boom',
            Pos(1, 1, 1),
            'x',
            key='a',
            first_position=Pos(0, 1, 0),
            filename='f.syml',
        )

        assert str(without_filename) == '1:1: boom\nx'
        assert str(with_filename) == 'f.syml:1:1: boom\nx'

    def test_line_text_is_rendered_through_printable_escaping(self) -> None:
        """A non-printable character in `line_text` is rendered as its Python escape."""
        error = ParseError('boom', Pos(0, 1, 0), 'a\xa0b')

        assert str(error) == '1:0: boom\na\\xa0b'
        assert error.line_text == 'a\xa0b'

    def test_filename_is_rendered_through_printable_escaping(self) -> None:
        r"""A `\n`, an ANSI escape, and a lone surrogate in `filename` do not break the two-line shape."""
        error = ParseError('boom', Pos(2, 2, 0), 'a: 2', filename='x\n\x1b[2J\udcff.syml')

        rendered = str(error)

        assert rendered == 'x\\n\\x1b[2J\\udcff.syml:2:0: boom\na: 2'
        assert rendered.count('\n') == 1
        rendered.encode('utf-8')  # must not raise UnicodeEncodeError
        assert error.message.startswith('x\n\x1b[2J\udcff.syml: ')


class TestDuplicateKeyErrorMessage:
    """Contract 03 §Messages: `DuplicateKeyError.message` is `Duplicate key '<key>'`."""

    def test_message_embeds_the_repeated_key(self) -> None:
        """`.message` reads `Duplicate key '<key>'` with no filename prefix when none is given."""
        with pytest.raises(DuplicateKeyError) as exc_info:
            syml.loads('a: 1\na: 2', filename='')

        assert exc_info.value.message == "Duplicate key 'a'"

    def test_spec_example_matches_exactly(self) -> None:
        r"""`SYML-SPECIFICATION.md`'s §8.3 example: `key: value1\nkey: value2` raises this exact message."""
        with pytest.raises(DuplicateKeyError) as exc_info:
            syml.loads('key: value1\nkey: value2\n')

        assert exc_info.value.message == "Duplicate key 'key'"


class TestParseErrorPickling:
    """Contract 03 §Test obligations 3: pickling preserves `str(e)`, `.message`, `.args`, and subclass attributes."""

    def test_parse_error_round_trips_through_pickle(self) -> None:
        """A plain `ParseError` survives a pickle round trip with its filename intact."""
        error = ParseError('boom', Pos(1, 1, 1), 'x', filename='f.syml')

        restored = pickle.loads(pickle.dumps(error))  # noqa: S301 - round-tripping our own just-pickled object

        assert str(restored) == str(error)
        assert restored.message == error.message
        assert restored.args == error.args

    def test_duplicate_key_error_round_trips_through_pickle(self) -> None:
        """`.key` and `.first_position` survive a pickle round trip alongside the base attributes."""
        error = DuplicateKeyError(
            "Duplicate key 'a'",
            Pos(9, 2, 0),
            'a: 2',
            key='a',
            first_position=Pos(0, 1, 0),
            filename='f.syml',
        )

        restored = pickle.loads(pickle.dumps(error))  # noqa: S301 - round-tripping our own just-pickled object

        assert str(restored) == str(error)
        assert restored.message == error.message
        assert restored.args == error.args
        assert restored.key == error.key
        assert restored.first_position == error.first_position
