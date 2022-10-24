# -*- coding: utf-8 -*-
import textwrap
from collections import OrderedDict
from io import StringIO
from unittest import TestCase

import ensure

import syml
from syml import exceptions, parser
from syml.utils import get_text_source

ensure = ensure.ensure


class TextOnlySymlParserTests(TestCase):
    def setUp(self):
        self.parser = parser.TextOnlySymlParser()

    def test_it_should_parse_a_simple_text_value(self):
        text = textwrap.dedent("yes")
        result = self.parser.parse(text)
        ensure(result.as_data()).equals(
            get_text_source(text, "yes"),
        )

    def test_it_should_parse_a_simple_multiline_list(self):
        text = textwrap.dedent(
            """
            - foo
            - bar
            - baz
        """
        )
        result = self.parser.parse(text)
        ensure(result.as_data()).equals(
            [
                get_text_source(text, "foo"),
                get_text_source(text, "bar"),
                get_text_source(text, "baz"),
            ]
        )

    def test_it_should_parse_a_simple_single_line_list(self):
        text = textwrap.dedent(
            """
            - foo
        """
        )
        result = self.parser.parse(text)
        ensure(result.as_data()).equals(
            [
                get_text_source(text, "foo"),
            ]
        )

    def test_it_should_parse_a_list_with_multiline_values(self):
        text = textwrap.dedent(
            """
            - foo
            - bar
              baz
        """
        )
        result = self.parser.parse(text)
        ensure(result.as_data()).equals(
            [
                get_text_source(text, "foo"),
                get_text_source(text, "bar\n  baz", "bar\nbaz", "bar\nbaz"),
            ]
        )

    def test_it_should_parse_a_list_with_embedded_mappings_values(self):
        text = textwrap.dedent(
            """
            - foo:
                bar
            - baz: boo
              blah:
                baloon
        """
        )
        result = self.parser.parse(text)
        ensure(result.as_data()).equals(
            [
                {get_text_source(text, "foo"): get_text_source(text, "bar")},
                {
                    get_text_source(text, "baz"): get_text_source(text, "boo"),
                    get_text_source(text, "blah"): get_text_source(text, "baloon"),
                },
            ]
        )

    def test_it_should_parse_a_simple_single_line_mapping(self):
        text = textwrap.dedent(
            """
            foo: bar
        """
        )
        result = self.parser.parse(text)
        ensure(result.as_data()).equals(
            OrderedDict(
                [
                    (get_text_source(text, "foo"), get_text_source(text, "bar")),
                ]
            )
        )

    def test_it_should_parse_a_simple_multiline_mapping(self):
        text = textwrap.dedent(
            """
            foo: bar
            baz: boo
        """
        )
        result = self.parser.parse(text)
        ensure(result.as_data()).equals(
            OrderedDict(
                [
                    (get_text_source(text, "foo"), get_text_source(text, "bar")),
                    (get_text_source(text, "baz"), get_text_source(text, "boo")),
                ]
            )
        )

    def test_it_should_parse_a_weirdly_nested_mapping(self):
        text = textwrap.dedent(
            """
            foo: bar: blah
            baz: boo
        """
        )
        result = self.parser.parse(text)
        ensure(result.as_data()).equals(
            OrderedDict(
                [
                    (get_text_source(text, "foo"), get_text_source(text, "bar: blah")),
                    (get_text_source(text, "baz"), get_text_source(text, "boo")),
                ]
            )
        )

    def test_it_should_parse_a_nested_mapping_with_list(self):
        text = textwrap.dedent(
            """
            foo:
              - bar
              - baz
            blah: boo
        """
        )
        result = self.parser.parse(text)
        ensure(result.as_data()).equals(
            OrderedDict(
                [
                    (
                        get_text_source(text, "foo"),
                        [
                            get_text_source(text, "bar"),
                            get_text_source(text, "baz"),
                        ],
                    ),
                    (get_text_source(text, "blah"), get_text_source(text, "boo")),
                ]
            )
        )

    def test_it_should_parse_a_nested_mapping_with_weirdly_nested_list(self):
        text = textwrap.dedent(
            """
            foo: - bar
            blah: boo
        """
        )
        result = self.parser.parse(text)
        ensure(result.as_data()).equals(
            OrderedDict(
                [
                    (get_text_source(text, "foo"), get_text_source(text, "- bar")),
                    (get_text_source(text, "blah"), get_text_source(text, "boo")),
                ]
            )
        )

    def test_it_should_parse_a_nested_list_with_mapping(self):
        text = textwrap.dedent(
            """
            - foo:
              - bar
              - baz
            - blah: boo
        """
        )
        result = self.parser.parse(text)
        ensure(result.as_data()).equals(
            [
                OrderedDict(
                    [
                        (
                            get_text_source(text, "foo"),
                            [
                                get_text_source(text, "bar"),
                                get_text_source(text, "baz"),
                            ],
                        ),
                    ]
                ),
                OrderedDict(
                    [
                        (get_text_source(text, "blah"), get_text_source(text, "boo")),
                    ]
                ),
            ]
        )

    def test_it_should_parse_comments_and_blanks(self):
        text = textwrap.dedent(
            """
        # A comment
        - foo:

          - bar
          # Something else entirely
          - baz

        - blah: boo # not a comment!

        """
        )
        result = self.parser.parse(text)
        ensure(result.as_data()).equals(
            [
                OrderedDict(
                    [
                        (
                            get_text_source(text, "foo"),
                            [
                                get_text_source(text, "bar"),
                                get_text_source(text, "baz"),
                            ],
                        ),
                    ]
                ),
                OrderedDict(
                    [
                        (
                            get_text_source(text, "blah"),
                            get_text_source(text, "boo # not a comment!"),
                        )
                    ]
                ),
            ]
        )

    def test_it_fails_parsing_weird_indentations(self):
        bad_yaml = textwrap.dedent(
            """
          - foo:
              - bar
         - baz
        - blah
        """
        )
        (ensure(self.parser.parse).called_with(bad_yaml).raises(exceptions.OutOfContextNodeError))


class BooleanSymlParserTests(TestCase):
    def setUp(self):
        self.parser = parser.BooleanSymlParser()

    def test_it_should_parse_a_simple_boolean_value(self):
        text = textwrap.dedent("yes")
        result = self.parser.parse(text)
        ensure(result.as_data()).equals(
            get_text_source(text, "yes", value=True),
        )

    def test_it_should_parse_mixed_boolean_values(self):
        text = textwrap.dedent(
            """
            - foo
            - yes
            - false
        """
        )
        result = self.parser.parse(text)
        ensure(result.as_data()).equals(
            [
                get_text_source(text, "foo"),
                get_text_source(text, "yes", value=True),
                get_text_source(text, "false", value=False),
            ]
        )


class SimpleParserFunctionTests(TestCase):
    def test_it_should_parse_a_simple_list(self):
        text = textwrap.dedent(
            """
            - foo
            - yes
            - false
        """
        )
        result = parser.parse(text)
        ensure(result).equals(
            [
                "foo",
                "yes",
                "false",
            ]
        )

    def test_it_should_parse_whats_in_the_readme_text_only(self):
        text = textwrap.dedent(
            """
            foo:
              - bar
              - baz
              - blah
                boo

            booleans?:
              - yes
              - no
              - true
              - false
              - on
              - off
        """
        )
        result = syml.loads(text)
        ensure(result).equals(
            {
                "foo": [
                    "bar",
                    "baz",
                    "blah\nboo",
                ],
                "booleans?": [
                    "yes",
                    "no",
                    "true",
                    "false",
                    "on",
                    "off",
                ],
            }
        )

    def test_it_should_parse_whats_in_the_readme_with_booleans(self):
        text = textwrap.dedent(
            """
            foo:
              - bar
              - baz
              - blah
                boo

            booleans?:
              - yes
              - no
              - true
              - false
              - on
              - off
        """
        )
        buf = StringIO(text)
        result = syml.load(buf, booleans=True)
        ensure(result).equals(
            {
                "foo": [
                    "bar",
                    "baz",
                    "blah\nboo",
                ],
                "booleans?": [
                    True,
                    False,
                    True,
                    False,
                    True,
                    False,
                ],
            }
        )
