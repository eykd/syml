# -*- coding: utf-8 -*-
import textwrap
from collections import OrderedDict
from io import StringIO
from unittest import TestCase

import pytest

import syml
from syml import exceptions, parser
from syml.types import Source


class TextOnlySymlParserTests(TestCase):
    def setUp(self):
        self.parser = parser.TextOnlySymlParser()

    def test_it_should_parse_a_simple_text_value(self):
        text = textwrap.dedent("true")
        result = self.parser.parse(text)
        assert result.as_data() == Source.from_text(text, "true")

    def test_it_should_parse_a_simple_multiline_list(self):
        text = textwrap.dedent(
            """
            - foo
            - bar
            - baz
            """
        )
        result = self.parser.parse(text)
        assert result.as_data() == [
            Source.from_text(text, "foo"),
            Source.from_text(text, "bar"),
            Source.from_text(text, "baz"),
        ]

    def test_it_should_parse_a_simple_single_line_list(self):
        text = textwrap.dedent(
            """
            - foo
            """
        )
        result = self.parser.parse(text)
        assert result.as_data() == [
            Source.from_text(text, "foo"),
        ]

    def test_it_should_parse_a_list_with_multiline_values(self):
        text = textwrap.dedent(
            """
            - foo
            - bar
              baz
            """
        )
        result = self.parser.parse(text)
        assert result.as_data() == [
            Source.from_text(text, "foo"),
            Source.from_text(text, "bar\n  baz", "bar\nbaz", "bar\nbaz"),
        ]

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
        assert result.as_data() == [
            {Source.from_text(text, "foo"): Source.from_text(text, "bar")},
            {
                Source.from_text(text, "baz"): Source.from_text(text, "boo"),
                Source.from_text(text, "blah"): Source.from_text(text, "baloon"),
            },
        ]

    def test_it_should_parse_a_simple_single_line_mapping(self):
        text = textwrap.dedent(
            """
            foo: bar
            """
        )
        result = self.parser.parse(text)
        assert result.as_data() == OrderedDict(
            [
                (Source.from_text(text, "foo"), Source.from_text(text, "bar")),
            ]
        )

    def test_it_should_parse_a_simple_multiline_mapping(self):
        text = textwrap.dedent(
            """
            foo: bar
            baz: boo
            """
        )
        result = self.parser.parse(text)
        assert result.as_data() == OrderedDict(
            [
                (Source.from_text(text, "foo"), Source.from_text(text, "bar")),
                (Source.from_text(text, "baz"), Source.from_text(text, "boo")),
            ]
        )

    def test_it_should_parse_a_weirdly_nested_mapping(self):
        text = textwrap.dedent(
            """
            foo: bar: blah
            baz: boo
            """
        )
        result = self.parser.parse(text)
        assert result.as_data() == OrderedDict(
            [
                (Source.from_text(text, "foo"), Source.from_text(text, "bar: blah")),
                (Source.from_text(text, "baz"), Source.from_text(text, "boo")),
            ]
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
        assert result.as_data() == OrderedDict(
            [
                (
                    Source.from_text(text, "foo"),
                    [
                        Source.from_text(text, "bar"),
                        Source.from_text(text, "baz"),
                    ],
                ),
                (Source.from_text(text, "blah"), Source.from_text(text, "boo")),
            ]
        )

    def test_it_should_parse_a_nested_mapping_with_weirdly_nested_list(self):
        text = textwrap.dedent(
            """
            foo: - bar
            blah: boo
            """
        )
        result = self.parser.parse(text)
        assert result.as_data() == OrderedDict(
            [
                (Source.from_text(text, "foo"), Source.from_text(text, "- bar")),
                (Source.from_text(text, "blah"), Source.from_text(text, "boo")),
            ]
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
        assert result.as_data() == [
            OrderedDict(
                [
                    (
                        Source.from_text(text, "foo"),
                        [
                            Source.from_text(text, "bar"),
                            Source.from_text(text, "baz"),
                        ],
                    ),
                ]
            ),
            OrderedDict(
                [
                    (Source.from_text(text, "blah"), Source.from_text(text, "boo")),
                ]
            ),
        ]

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
        assert result.as_data() == [
            OrderedDict(
                [
                    (
                        Source.from_text(text, "foo"),
                        [
                            Source.from_text(text, "bar"),
                            Source.from_text(text, "baz"),
                        ],
                    ),
                ]
            ),
            OrderedDict(
                [
                    (
                        Source.from_text(text, "blah"),
                        Source.from_text(text, "boo # not a comment!"),
                    )
                ]
            ),
        ]

    def test_it_fails_parsing_weird_indentations(self):
        bad_yaml = textwrap.dedent(
            """
              - foo:
                  - bar
             - baz
            - blah
            """
        )
        with pytest.raises(exceptions.OutOfContextNodeError):
            self.parser.parse(bad_yaml)


class BooleanSymlParserTests(TestCase):
    def setUp(self):
        self.parser = parser.BooleanSymlParser()

    def test_it_should_parse_a_simple_boolean_value(self):
        text = textwrap.dedent("true")
        result = self.parser.parse(text)
        assert result.as_data() == Source.from_text(text, "true", value=True)

    def test_it_should_parse_mixed_boolean_values(self):
        text = textwrap.dedent(
            """
            - foo
            - true
            - false
            """
        )
        result = self.parser.parse(text)
        assert result.as_data() == [
            Source.from_text(text, "foo"),
            Source.from_text(text, "true", value=True),
            Source.from_text(text, "false", value=False),
        ]


class SimpleParserFunctionTests(TestCase):
    def test_it_should_parse_a_simple_list(self):
        text = textwrap.dedent(
            """
            - foo
            - true
            - false
            """
        )
        result = parser.parse(text)
        assert result == [
            "foo",
            "true",
            "false",
        ]

    def test_it_should_parse_whats_in_the_readme_text_only(self):
        text = textwrap.dedent(
            """
            foo:
              - bar
              - baz
              - blah
                boo
                baloon

            booleans?:
              - True
              - False
              - true
              - false
              - TRUE
              - FALSE
            """
        )
        result = syml.loads(text)
        assert result == {
            "foo": [
                "bar",
                "baz",
                "blah\nboo\nbaloon",
            ],
            "booleans?": [
                "True",
                "False",
                "true",
                "false",
                "TRUE",
                "FALSE",
            ],
        }

    def test_it_should_parse_whats_in_the_readme_with_booleans(self):
        text = textwrap.dedent(
            """
            foo:
              - bar
              - baz
              - blah
                boo

            booleans?:
              - True
              - False
              - true
              - false
              - TRUE
              - FALSE
            """
        )
        buf = StringIO(text)
        result = syml.load(buf, booleans=True)
        assert result == {
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
