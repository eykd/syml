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
    """`decode_double_quoted` is a stub pending US6's escape table (Contract 04)."""

    def test_it_should_raise_not_implemented_error(self) -> None:
        """The escape table is not implemented yet; the stub raises `NotImplementedError`."""
        with pytest.raises(NotImplementedError):
            quoting.decode_double_quoted('"foo"')
