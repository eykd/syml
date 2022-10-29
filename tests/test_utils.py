import textwrap
from unittest import TestCase

from ensure import ensure

from syml import utils


class GetLineTests(TestCase):
    def setUp(self):
        self.text = textwrap.dedent(
            """

        foo
            bar
                baz blah blargh
        boo
        """
        )

    def test_it_should_get_the_line(self):
        (ensure(utils.get_line).called_with(self.text, 5).equals("        baz blah blargh\n"))

    def test_it_should_get_a_blank_str_for_bad_line(self):
        (ensure(utils.get_line).called_with(self.text, 99).equals(""))
