"""Tests for `syml.quoting`."""

import pytest

from syml import parsers, quoting


class TestWhereQuotingIsRecognized:
    """D2: quoting is only recognized at an inline value position (Contract 04)."""

    def test_it_should_decode_a_single_quoted_inline_key_value(self) -> None:
        """`key: 'a'` is an inline position, so the quotes are stripped (US6 D2)."""
        parser = parsers.SymlParser()
        result = parser.parse("key: 'a'")
        assert result.as_data() == {'key': 'a'}


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
