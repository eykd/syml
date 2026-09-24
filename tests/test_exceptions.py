"""Tests for src/syml/exceptions.py."""

from __future__ import annotations

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
                'a: 1\n  - foo\nc: 1\n',
                OutOfContextNodeError,
                '  - foo',
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
