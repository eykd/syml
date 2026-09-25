"""Tests for src/syml/exceptions.py."""

from __future__ import annotations

import pathlib
import pickle  # noqa: S403 - test-only, deserializes only what this test just pickled
import re

import pytest

import syml
from syml.basetypes import Pos
from syml.exceptions import (
    DuplicateKeyError,
    OutOfContextNodeError,
    ParseError,
    UnrepresentableValueError,
    error_message,
    is_comment_shaped,
    is_document_marker,
    needs_space_after_marker,
    would_be_key,
)
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
        assert result.message == 'Invalid UTF-8 (byte 0xff); save the file as UTF-8'


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


class TestSpecificationSection113MatchesSymlAll:
    """Contract 05 §Test obligation 2: §11.3's class list matches `syml.__all__` (`syml-xreq.7`).

    `DocumentLimitError` is documented in §11.3's closing paragraph, below
    the "MUST expose these exact class names" sentence, as a *reserved*
    name for implementations that enforce §13.4 -- `syml` enforces none,
    so it is deliberately absent from both the fenced class block's
    required-export classes and `syml.__all__`.
    """

    _SPEC_PATH = pathlib.Path(__file__).parent.parent / 'SYML-SPECIFICATION.md'
    _CLASS_HEADER_RE = re.compile(r'^([A-Za-z]+)\(([A-Za-z]+)\)$', re.MULTILINE)

    def _section_11_3_text(self) -> str:
        """Return the full text of §11.3, from its heading to the next `## ` heading."""
        text = self._SPEC_PATH.read_text(encoding='utf-8')
        start = text.index('### 11.3 Exceptions')
        end = text.index('\n## ', start)
        return text[start:end]

    def _section_11_3_class_names(self) -> list[str]:
        """Extract every `Name(Base)` header from the §11.3 fenced code block."""
        section = self._section_11_3_text()
        block_start = section.index('```\n') + len('```\n')
        block_end = section.index('\n```', block_start)
        block = section[block_start:block_end]
        return [name for name, _base in self._CLASS_HEADER_RE.findall(block)]

    def test_every_required_export_class_in_section_11_3_is_in_syml_all(self) -> None:
        """Every §11.3 fenced-block class is exported in `syml.__all__`."""
        class_names = self._section_11_3_class_names()

        assert class_names, 'expected to find at least one class header in §11.3'
        for name in class_names:
            assert name in syml.__all__, f'{name} is documented in §11.3 but missing from syml.__all__'

    def test_document_limit_error_is_reserved_not_exported(self) -> None:
        """`DocumentLimitError` is named in §11.3's closing paragraph but is not a required export."""
        section = self._section_11_3_text()
        class_names = self._section_11_3_class_names()

        assert (
            'DocumentLimitError' not in class_names
        ), '§11.3 should reserve the name in prose, not the required-export class block'
        assert '`DocumentLimitError(ParseError)`' in section, '§11.3 should still document the reserved name'
        assert 'DocumentLimitError' not in syml.__all__
        assert not hasattr(syml, 'DocumentLimitError')


class TestErrorMessage:
    """Contract 05 §Surface: `error_message` carries the filename (red-team pass 14)."""

    def test_error_message_omits_filename_when_none(self) -> None:
        """`description` alone when `filename` is `None`."""
        assert error_message('Invalid encoding', None) == 'Invalid encoding'

    def test_error_message_prefixes_filename_when_given(self) -> None:
        """`f'{filename}: {description}'` when `filename` is given."""
        assert error_message('Invalid encoding', 'doc.syml') == 'doc.syml: Invalid encoding'

    def test_error_message_windows_a_hostile_filename(self) -> None:
        """A multi-megabyte `filename` is windowed to 80 chars plus an ellipsis marker (syml-cjk2.5)."""
        huge_filename = 'F' * 2_000_000

        result = error_message('Invalid encoding', huge_filename)

        assert result == f'{'F' * 80}…: Invalid encoding'


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

    def test_str_and_message_are_bounded_for_a_hostile_filename(self) -> None:
        """A multi-megabyte `filename` is windowed to 80 chars plus an ellipsis in both renderings (syml-cjk2.5)."""
        huge_filename = 'F' * 2_000_000
        windowed = f'{'F' * 80}…'
        error = ParseError('boom', Pos(1, 1, 1), 'x', filename=huge_filename)

        assert error.message == f'{windowed}: boom'
        assert str(error) == f'{windowed}:1:1: boom\nx'

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


class TestOutOfContextNodeErrorMessageColumnsAndForms:
    """Contract 03 §Messages: form 1 ('does not fit any open block') vs form 2 (KIND/OTHER mismatch)."""

    @pytest.mark.parametrize(
        ('document', 'expected_message'),
        [
            pytest.param(
                'k:\n- a\n- b',
                'Line 2, at column 0, is a list item, but the open block at column 0 holds keys; '
                "open blocks are at column 0. Hint: a list under a key must be indented past the key's column.",
                id='US2-1_list_item_vs_keys_with_hint_b',
            ),
            pytest.param(
                '- item\nkey: value',
                'Line 2, at column 0, is a key, but the open block at column 0 holds list items; '
                'open blocks are at column 0.',
                id='key_vs_list_items',
            ),
            pytest.param(
                'a:\n  b: 1\n  plain',
                'Line 3, at column 2, is a text line, but the open block at column 2 holds keys; '
                'open blocks are at columns 0 and 2.',
                id='text_line_vs_keys_two_columns',
            ),
            pytest.param(
                '- a\nb',
                'Line 2, at column 0, is a text line, but the open block at column 0 holds list items; '
                'open blocks are at column 0.',
                id='text_line_vs_list_items',
            ),
            pytest.param(
                'a:\n  b:\n    c: 1\n   d: 2',
                'Line 4, at column 3, does not fit any open block; open blocks are at columns 0, 2 and 4.',
                id='three_open_columns_no_hint',
            ),
        ],
    )
    def test_message_names_kind_other_and_open_columns(self, document: str, expected_message: str) -> None:
        """`.message` matches Contract 03's KIND/OTHER form and column-list formatting exactly."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads(document)

        assert exc_info.value.message == expected_message


class TestOutOfContextNodeErrorTextValueClause:
    """Contract 03 §Text-value clause: present for a block value, and an inline value with a continuation."""

    def test_str_matches_us2_9_exactly(self) -> None:
        """US2-9: `str(e)` for an inline value with no continuation carries no text-value clause."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('k:\n  a: 1\n b: 2')

        assert (
            str(exc_info.value)
            == '3:1: Line 3, at column 1, does not fit any open block; open blocks are at columns 0 and 2.\n b: 2'
        )

    def test_us2_10_filename_prefixes_str_and_message(self) -> None:
        """US2-10: the same document loaded with a filename prefixes both `str(e)` and `.message`."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('k:\n  a: 1\n b: 2', filename='f.syml')

        assert str(exc_info.value).startswith('f.syml:3:1: ')
        assert exc_info.value.message.startswith('f.syml: ')

    def test_block_value_clause_us1_18(self) -> None:
        """US1-18: a block value's baseline names the column the author most likely meant."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('k: a\n    b\n  c')

        assert exc_info.value.message == (
            'Line 3, at column 2, does not fit any open block; open blocks are at column 0; '
            'the open value continues at column 4.'
        )

    def test_inline_value_with_continuation_clause_us2_7(self) -> None:
        """US2-7: an inline value that already has one continuation also gets the clause."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('k:\n  a\n\xa0\n  b')

        assert exc_info.value.message == (
            'Line 3, at column 0, is a text line, but the open block at column 0 holds keys; '
            'open blocks are at column 0; the open value continues at column 2.'
        )


class TestOutOfContextNodeErrorHintA:
    """Contract 03 §Hints (a): would-be-key hint, on the failing line and on the line above."""

    def test_failing_line_names_the_would_be_key_us1_8(self) -> None:
        """US1-8: a same-column key with an uppercase character raises at line 2, naming it in the hint."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('name: a\nfirstName: b\nage: 3')

        assert exc_info.value.position.line == 2
        assert "Hint: 'firstName' is not a key" in exc_info.value.message

    def test_line_above_names_the_would_be_key(self) -> None:
        """The block value's own first line, one column below the failing key line, still gets the hint."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('config:\n  Host: x\n port: 1')

        assert "Hint: 'Host' is not a key" in exc_info.value.message

    def test_line_above_skips_a_column_0_comment(self) -> None:
        """A column-0 comment between the value's first line and the failing line is skipped (R-18)."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('config:\n  Host: x\n# c\n port: 1')

        assert "Hint: 'Host' is not a key" in exc_info.value.message

    def test_punctuation_key_gets_a_hint_too(self) -> None:
        """A lowercase-but-punctuated run still fails the key pattern and gets a hint (README's former lead key)."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('a: 1\nbooleans?: x')

        assert exc_info.value.message == (
            'Line 2, at column 0, is a text line, but the open block at column 0 holds keys; '
            "open blocks are at column 0. Hint: 'booleans?' is not a key; a key is lowercase ASCII letters, "
            "digits, '-' and '_', starting with a letter."
        )

    def test_no_hint_when_colon_is_not_followed_by_whitespace(self) -> None:
        """`Key:value` (no space after the colon) is not a would-be-key candidate at all."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('a: 1\nKey:value')

        assert 'Hint' not in exc_info.value.message


class TestOutOfContextNodeErrorHintGating:
    """Contract 03 §Hints (a) Gating (red team outer iteration 7): dialogue in prose gets no false hint."""

    def test_no_hint_when_a_later_continuation_line_would_be_a_key(self) -> None:
        """`Carol: yo` is a continuation, not the value's first line, so it never qualifies."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('- scene:\n    Bob: hi\n    Carol: yo\n   Alice: hey')

        assert 'Hint' not in exc_info.value.message
        assert exc_info.value.message.endswith('; the open value continues at column 4.')

    def test_no_hint_when_the_failing_line_itself_lexes_as_text(self) -> None:
        """Even though `Bob: hi` is the value's first line, the failing line lexed as text, not structure."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('- scene:\n    Bob: hi\n   Alice: hey')

        assert exc_info.value.message == (
            'Line 3, at column 3, does not fit any open block; open blocks are at columns 0 and 2; '
            'the open value continues at column 4.'
        )

    def test_no_hint_when_failing_column_is_not_an_open_mapping_column(self) -> None:
        """`Port: 1` lexes as text, and column 1 is not an open `Mapping` column either."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('config:\n  Host: x\n Port: 1')

        assert 'Hint' not in exc_info.value.message


class TestOutOfContextNodeErrorHintC:
    """Contract 03 §Hints (c) (D26): missing-space-after-marker hint, on the failing line and the line above."""

    def test_key_missing_space_under_a_mapping(self) -> None:
        """`port:8080` (no space after the colon) under an open `Mapping` gets the missing-space hint."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('server:\n  host: x\n  port:8080')

        assert exc_info.value.message == (
            'Line 3, at column 2, is a text line, but the open block at column 2 holds keys; '
            'open blocks are at columns 0 and 2. Hint: a key or list marker needs a space after it.'
        )

    def test_list_marker_missing_space_under_a_list(self) -> None:
        """`-b` (no space after the list marker) under an open `List` gets the missing-space hint."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('l:\n  - a\n  -b')

        assert exc_info.value.message == (
            'Line 3, at column 2, is a text line, but the open block at column 2 holds list items; '
            'open blocks are at columns 0 and 2. Hint: a key or list marker needs a space after it.'
        )

    def test_line_above_gets_the_missing_space_hint(self) -> None:
        """The block value's own first line, missing its colon-space, still gets the hint via the look-back."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('k:\n  port:8080\n- x')

        assert 'Hint: a key or list marker needs a space after it.' in exc_info.value.message

    def test_no_hint_when_the_failing_column_is_not_an_open_block(self) -> None:
        """Form 1 (`does not fit any open block`) never gets hint (c) — the real problem is indentation."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('server:\n  host: x\n port:8080')

        assert exc_info.value.message == (
            'Line 3, at column 1, does not fit any open block; open blocks are at columns 0 and 2.'
        )

    def test_no_hint_for_a_document_marker_shaped_line(self) -> None:
        """`---`/`--x` never gets hint (c) — mid-file document markers get hint (e), not hint (c)."""
        assert needs_space_after_marker('---') is False
        assert needs_space_after_marker('--x') is False


class TestOutOfContextNodeErrorHintD:
    """Contract 03 §Hints (d) (D27): indented-comment hint, on the failing line only."""

    def test_indented_hash_comment_gets_the_hint(self) -> None:
        """The repro from `syml-cjk2.11`: commenting out a key in place raises on the next real key."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('server:\n  host: a\n  # port: 80\n  port: 81')

        assert exc_info.value.message == (
            'Line 3, at column 2, is a text line, but the open block at column 2 holds keys; '
            "open blocks are at columns 0 and 2. Hint: comments must start at column 0; an indented '#' line is text."
        )

    def test_indented_slash_slash_comment_gets_the_hint(self) -> None:
        """`//` is the other comment marker (Contract 03 §Behaviour, R-18)."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('server:\n  host: a\n  // port: 80\n  port: 81')

        assert "Hint: comments must start at column 0; an indented '#' line is text." in exc_info.value.message

    def test_form_1_also_gets_the_hint(self) -> None:
        """Unlike hint (c), (d) is not gated to form 2 — an odd-column comment still names the real problem."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('server:\n  host: a\n # comment\n  port: 81')

        assert exc_info.value.message == (
            'Line 3, at column 1, does not fit any open block; open blocks are at columns 0 and 2. '
            "Hint: comments must start at column 0; an indented '#' line is text."
        )

    def test_hint_d_wins_over_hint_a_when_the_comment_has_no_space(self) -> None:
        """`#port: 80` matches hint (a)'s `RUN:` pattern too, but (d) is checked first (a `#`-led line is a comment)."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('server:\n  host: a\n  #port: 80\n  port: 81')

        assert "Hint: comments must start at column 0; an indented '#' line is text." in exc_info.value.message
        assert 'is not a key' not in exc_info.value.message


class TestOutOfContextNodeErrorHintE:
    """Contract 03 §Hints (e) (D27): document-marker hint, on the failing line only."""

    def test_mid_file_triple_dash_gets_the_hint(self) -> None:
        """The repro from `syml-cjk2.11`: a YAML document separator is just text in SYML."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('k: v\n---\nj: w')

        assert exc_info.value.message == (
            'Line 2, at column 0, is a text line, but the open block at column 0 holds keys; '
            'open blocks are at column 0. Hint: SYML has no document markers.'
        )

    def test_end_marker_gets_the_hint_too(self) -> None:
        """`...` is YAML's end-of-document marker; SYML has no equivalent either."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('k:\n  v\n...\n')

        assert exc_info.value.message == (
            'Line 3, at column 0, is a text line, but the open block at column 0 holds keys; '
            'open blocks are at column 0; the open value continues at column 2. '
            'Hint: SYML has no document markers.'
        )

    def test_double_dash_does_not_get_the_hint(self) -> None:
        """`--x` is not a document marker (only `---` and `...` are, per `is_document_marker`'s truth table)."""
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('server:\n  host: a\n  --x\n  port: 81')

        assert 'Hint' not in exc_info.value.message


class TestOutOfContextNodeErrorPosition:
    """Contract 03 §Behaviour: a dropped column-0 comment keeps the original text's line numbers."""

    def test_dropped_comment_line_still_counts_toward_the_line_number(self) -> None:
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('a: 1\n# c\n- x')

        assert exc_info.value.position == Pos(9, 3, 0)
        assert exc_info.value.message == (
            'Line 3, at column 0, is a list item, but the open block at column 0 holds keys; '
            'open blocks are at column 0.'
        )


class TestOutOfContextNodeErrorEscaping:
    """Contract 03 §Surface: an unprintable character in `line_text` or a would-be key is rendered, not echoed."""

    def test_line_text_escape_us2_7(self) -> None:
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('k:\n  a\n\xa0\n  b')

        error = exc_info.value
        assert error.line_text == '\xa0'
        assert str(error).splitlines()[1] == '\\xa0'

    def test_hint_key_escape(self) -> None:
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('a: 1\n\x1b[31mX: y')

        rendered = str(exc_info.value)
        assert '\x1b' not in rendered
        assert rendered.splitlines()[1] == '\\x1b[31mX: y'
        assert "Hint: '\\x1b[31mX' is not a key" in exc_info.value.message


class TestOutOfContextNodeErrorBoundedSize:
    """Contract 03 §Surface/§Hints (a): a hostile long line yields a bounded `.message`/`str(e)` (syml-s9p9.9)."""

    def test_bounded_message_and_str_for_a_hostile_one_megabyte_line(self) -> None:
        r"""A 1 MB `\x00`-run before a bare `:` used to yield a multi-megabyte `.message`/`str(e)`."""
        hostile_run = '\x00' * 1_000_000
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads(f'a: 1\n{hostile_run}: x')

        error = exc_info.value
        # `.line_text` itself carries the raw, untruncated line (Contract 05 §`line_text`).
        assert error.line_text == f'{hostile_run}: x'
        # Both the hint's would-be-key quote and `str(e)`'s line text are windowed,
        # so neither `.message` nor `str(e)` scales with the hostile line's length.
        assert len(error.message) < 1_000
        assert len(str(error)) < 1_000


class TestDuplicateKeyErrorBoundedSize:
    """Contract 03 §Messages/§Bounded rendering: a hostile long key yields a bounded description (syml-s9p9.14)."""

    def test_bounded_message_and_str_for_a_duplicated_one_megabyte_key(self) -> None:
        r"""A key repeating 1 MB used to yield a multi-megabyte `.message`/`str(e)`."""
        key = 'a' * 1_000_000
        with pytest.raises(DuplicateKeyError) as exc_info:
            syml.loads(f'{key}: 1\n{key}: 2')

        error = exc_info.value
        # `.key` still carries the full, untruncated key (Contract 03 §Messages: "unchanged attributes").
        assert error.key == key
        assert len(error.message) < 1_000
        assert len(str(error)) < 1_000


class TestOutOfContextNodeErrorSC007:
    """Contract 03 §Test obligations item 7: SC-007's plain context error."""

    def test_position_and_no_hint(self) -> None:
        with pytest.raises(OutOfContextNodeError) as exc_info:
            syml.loads('a: 1\nb')

        rendered = str(exc_info.value)
        lines = rendered.splitlines()
        assert lines[0].startswith('2:0: ')
        assert 'Hint' not in lines[0]
        assert lines[1] == 'b'


class TestWouldBeKey:
    """Contract 03 §Hints (a): the standalone `would_be_key` helper's own truth table."""

    @pytest.mark.parametrize(
        ('line_text', 'expected'),
        [
            pytest.param('key: value', None, id='already_a_valid_key'),
            pytest.param('  key: value', None, id='indented_valid_key'),
            pytest.param('firstName: b', 'firstName', id='uppercase_run'),
            pytest.param('a plain line', None, id='no_colon_at_all'),
            pytest.param('Key:value', None, id='colon_not_followed_by_whitespace_or_eol'),
            pytest.param('lastWord:', 'lastWord', id='colon_at_end_of_line'),
        ],
    )
    def test_would_be_key(self, line_text: str, expected: str | None) -> None:
        assert would_be_key(line_text) == expected


class TestNeedsSpaceAfterMarker:
    """Contract 03 §Hints (c): the standalone `needs_space_after_marker` helper's own truth table."""

    @pytest.mark.parametrize(
        ('line_text', 'expected'),
        [
            pytest.param('key:value', True, id='key_colon_no_space'),
            pytest.param('  key:value', True, id='indented_key_colon_no_space'),
            pytest.param('key: value', False, id='key_colon_with_space'),
            pytest.param('key:', False, id='key_colon_at_end_of_line'),
            pytest.param('-x', True, id='list_marker_no_space'),
            pytest.param('  -x', True, id='indented_list_marker_no_space'),
            pytest.param('- x', False, id='list_marker_with_space'),
            pytest.param('---', False, id='document_marker'),
            pytest.param('--x', False, id='double_dash_marker'),
            pytest.param('...', False, id='end_marker'),
            pytest.param('a plain line', False, id='no_marker_at_all'),
        ],
    )
    def test_needs_space_after_marker(self, line_text: str, *, expected: bool) -> None:
        assert needs_space_after_marker(line_text) is expected


class TestIsCommentShaped:
    """Contract 03 §Hints (d): the standalone `is_comment_shaped` helper's own truth table."""

    @pytest.mark.parametrize(
        ('line_text', 'expected'),
        [
            pytest.param('# comment', True, id='hash_at_column_0'),
            pytest.param('  # comment', True, id='indented_hash'),
            pytest.param('  // comment', True, id='indented_slash_slash'),
            pytest.param('  #port: 80', True, id='indented_hash_no_space'),
            pytest.param('key: value', False, id='ordinary_key'),
            pytest.param('  key: value', False, id='indented_ordinary_key'),
            pytest.param('- item', False, id='list_item'),
            pytest.param('a plain line', False, id='no_marker_at_all'),
            pytest.param(' /path', False, id='single_slash_not_a_comment'),
        ],
    )
    def test_is_comment_shaped(self, line_text: str, *, expected: bool) -> None:
        assert is_comment_shaped(line_text) is expected


class TestIsDocumentMarker:
    """Contract 03 §Hints (e): the standalone `is_document_marker` helper's own truth table."""

    @pytest.mark.parametrize(
        ('line_text', 'expected'),
        [
            pytest.param('---', True, id='triple_dash'),
            pytest.param('  ---', True, id='indented_triple_dash'),
            pytest.param('...', True, id='end_marker'),
            pytest.param('  ...', True, id='indented_end_marker'),
            pytest.param('--- ', True, id='trailing_space'),
            pytest.param('--- x', False, id='trailing_content'),
            pytest.param('--x', False, id='double_dash_only'),
            pytest.param('----', False, id='four_dashes'),
            pytest.param('....', False, id='four_dots'),
            pytest.param('a plain line', False, id='no_marker_at_all'),
        ],
    )
    def test_is_document_marker(self, line_text: str, *, expected: bool) -> None:
        assert is_document_marker(line_text) is expected


class TestUnrepresentableValueErrorPathAndStr:
    """D30: `.path` defaults to `()`; `str(e)` is the message alone, plus a path clause."""

    def test_it_should_default_path_to_the_empty_tuple(self) -> None:
        error = UnrepresentableValueError('boom')
        assert error.path == ()

    def test_it_should_render_str_as_the_message_alone_at_the_root(self) -> None:
        error = UnrepresentableValueError('boom')
        assert str(error) == 'boom'

    def test_it_should_store_the_given_path(self) -> None:
        error = UnrepresentableValueError('boom', ('a', 'b', 1))
        assert error.path == ('a', 'b', 1)

    def test_it_should_append_the_path_as_a_subscript_clause(self) -> None:
        error = UnrepresentableValueError('boom', ('a', 'b', 1))
        assert str(error) == "boom at ['a']['b'][1]"

    def test_it_should_not_render_a_tuple_repr_of_args(self) -> None:
        error = UnrepresentableValueError('boom', ('a',))
        assert str(error) != str(('boom', ('a',)))
