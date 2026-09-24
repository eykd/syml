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


class TestDecodeDoubleQuoted:
    """`decode_double_quoted` is a stub pending US6's escape table (Contract 04)."""

    def test_it_should_raise_not_implemented_error(self) -> None:
        """The escape table is not implemented yet; the stub raises `NotImplementedError`."""
        with pytest.raises(NotImplementedError):
            quoting.decode_double_quoted('"foo"')
