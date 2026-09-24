"""Tests for `syml.quoting`."""

import pytest

from syml import exceptions, parsers, quoting


class TestWhereQuotingIsRecognized:
    """D2: quoting is only recognized at an inline value position (Contract 04)."""

    def test_it_should_decode_a_single_quoted_inline_key_value(self) -> None:
        """`key: 'a'` is an inline position, so the quotes are stripped (US6 D2)."""
        parser = parsers.SymlParser()
        result = parser.parse("key: 'a'")
        assert result.as_data() == {'key': 'a'}

    def test_it_should_not_decode_a_quoted_bare_root_scalar_line(self) -> None:
        """A bare root-scalar line is never an inline position, so a well-formed quote stays literal text (D2).

        `syml.SYML-SPEC-REVIEW.md` D2: bare lines (root scalars, block values, continuation
        lines) are never quote-decoded. Today the grammar's `line = indent (... / value) &eol`
        falls through directly to `value = structure / quoted_value / data`, so a terminated
        quote on a bare root-scalar line still matches `quoted_value` and gets decoded. Expected
        to fail until the grammar stops trying `quoted_value` at the bare `line` position.
        """
        parser = parsers.SymlParser()
        result = parser.parse("'yes'")
        assert result.as_data() == "'yes'"


class TestDecodeSingleQuoted:
    """`decode_single_quoted` decodes a '...' literal (Contract 04)."""

    def test_it_should_decode_doubled_quotes_and_keep_backslashes_literal(self) -> None:
        """`''` decodes to one apostrophe; backslashes survive with no escape processing (US6.2, US6.3)."""
        assert quoting.decode_single_quoted("'it''s fine'") == "it's fine"
        assert quoting.decode_single_quoted("'hello\\nworld'") == 'hello\\nworld'


class TestDecodeDoubleQuoted:
    """`decode_double_quoted` decodes a "..." literal against the §4.7 escape table (Contract 04)."""

    def test_it_should_decode_the_escape_table(self) -> None:
        """Each §4.7 escape decodes to its table result (US6)."""
        assert quoting.decode_double_quoted(r'"hello\nworld"') == 'hello\nworld'
        assert quoting.decode_double_quoted(r'"a\tb"') == 'a\tb'
        assert quoting.decode_double_quoted(r'"a\rb"') == 'a\rb'
        assert quoting.decode_double_quoted(r'"a\\b"') == 'a\\b'
        assert quoting.decode_double_quoted(r'"a\/b"') == 'a/b'
        assert quoting.decode_double_quoted(r'"she said \"hi\""') == 'she said "hi"'
        assert quoting.decode_double_quoted(r'"☺"') == '☺'
        assert quoting.decode_double_quoted(r'"\u2603"') == '\u2603'
        assert quoting.decode_double_quoted(r'"\U0001F600"') == '\U0001f600'


class TestDecodeDoubleQuotedMalformed:
    """`decode_double_quoted` raises `QuotedStringDefect` for a bad decoded code point (Contract 04)."""

    def test_it_should_raise_on_a_surrogate_or_out_of_range_code_point(self) -> None:
        r"""`\ud800` is a surrogate and `\U00110000` is above U+10FFFF \u2014 both always errors (D3, US6.6, US6.7)."""
        with pytest.raises(quoting.QuotedStringDefect) as excinfo:
            quoting.decode_double_quoted(r'"\ud800"')
        assert excinfo.value.escape == '\\ud800'
        assert excinfo.value.code_point == 0xD800

        with pytest.raises(quoting.QuotedStringDefect) as excinfo:
            quoting.decode_double_quoted(r'"\U00110000"')
        assert excinfo.value.escape == '\\U00110000'
        assert excinfo.value.code_point == 0x110000


class TestDiagnoseMalformed:
    """`diagnose_malformed` reports the first invalid escape in a quote-guard fallthrough (Contract 04)."""

    def test_it_should_diagnose_the_first_invalid_or_incomplete_escape(self) -> None:
        r"""`\x` and an incomplete `\u12` are both reported as the offending `.escape` (US6.5)."""
        assert quoting.diagnose_malformed(r'"a\xb"') == '\\x'
        assert quoting.diagnose_malformed(r'"a\u12"') == '\\u12'

    def test_it_should_report_none_for_an_unterminated_value(self) -> None:
        """No defect found before end of line means merely unterminated, for either quote style (US6.9)."""
        assert quoting.diagnose_malformed('"unterminated') is None
        assert quoting.diagnose_malformed("'a''") is None

    def test_it_should_skip_valid_escapes_and_still_report_unterminated(self) -> None:
        r"""A valid `\n` or complete `A` escape is skipped whole before hitting end of line."""
        assert quoting.diagnose_malformed('"a\\n unterminated') is None
        assert quoting.diagnose_malformed('"a\\u0041 unterminated') is None

    def test_it_should_report_a_dangling_backslash_at_end_of_line(self) -> None:
        r"""A trailing `\` with nothing after it is its own defect: `escape == '\\'`."""
        assert quoting.diagnose_malformed('"abc\\') == '\\'


class TestQuoteGuardRule:
    """The quote-guard rule (§4.1, R-10): data beginning with a quote at an inline position is malformed."""

    def test_it_should_raise_malformed_with_the_diagnosed_escape_on_fallthrough(self) -> None:
        r"""`key: "a\xb"` fails to match `quoted_value` and falls through to `data_key_value`.

        The quote-guard must raise `MalformedQuotedStringError` diagnosed via `diagnose_malformed`
        (`escape == '\\x'`, `code_point is None`) rather than silently keeping the leading quote as text
        (Contract 04 §The quote-guard rule / §What the quote-guard reports).
        """
        parser = parsers.SymlParser()
        with pytest.raises(exceptions.MalformedQuotedStringError) as excinfo:
            parser.parse(r'key: "a\xb"')
        assert excinfo.value.escape == '\\x'
        assert excinfo.value.code_point is None
