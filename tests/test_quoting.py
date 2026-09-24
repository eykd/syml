"""Tests for `syml.quoting`."""

import pytest

from syml import quoting


class TestDecodeDoubleQuoted:
    """`decode_double_quoted` is a stub pending US6's escape table (Contract 04)."""

    def test_it_should_raise_not_implemented_error(self) -> None:
        """The escape table is not implemented yet; the stub raises `NotImplementedError`."""
        with pytest.raises(NotImplementedError):
            quoting.decode_double_quoted('"foo"')
