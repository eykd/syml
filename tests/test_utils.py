import textwrap

import pytest

from syml import utils


class TestGetLine:
    @pytest.fixture
    def text(self) -> str:
        return textwrap.dedent(
            """

        foo
            bar
                baz blah blargh
        boo
        """
        )

    def test_it_should_get_the_line(self, text: str) -> None:
        assert utils.get_line(text, 5) == '        baz blah blargh\n'

    def test_it_should_get_a_blank_str_for_bad_line(self, text: str) -> None:
        assert utils.get_line(text, 99) == ''
