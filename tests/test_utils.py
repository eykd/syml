import re
import textwrap
from unittest import TestCase

from ensure import ensure

from syml import utils
from syml.types import Pos


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


class GetCoordsOfStrIndexTests(TestCase):
    def setUp(self):
        self.text = textwrap.dedent(
            """

        foo
            bar
                baz blah blargh
        boo
        """
        )

    def test_returns_line_and_column_at_start_of_line(self):
        match = re.search("foo", self.text)
        start = match.start()
        (ensure(utils.get_coords_of_str_index).called_with(self.text, start).equals(Pos(start, 3, 0)))

    def test_returns_line_and_column_of_indented_text(self):
        match = re.search("bar", self.text)
        start = match.start()
        (ensure(utils.get_coords_of_str_index).called_with(self.text, start).equals(Pos(start, 4, 4)))

    def test_returns_line_and_column_of_midline_text(self):
        match = re.search("blah", self.text)
        start = match.start()
        (ensure(utils.get_coords_of_str_index).called_with(self.text, start).equals(Pos(start, 5, 12)))

    def test_returns_last_line_and_first_column_of_bad_index(self):
        (
            ensure(utils.get_coords_of_str_index)
            .called_with(self.text, len(self.text) + 5)
            .equals(Pos(len(self.text), 6, 0))
        )
