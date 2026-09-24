"""Tests for `syml.quoting`."""

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
