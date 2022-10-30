import textwrap
from collections import OrderedDict
from io import StringIO

import pytest

import syml
from syml import exceptions, parser
from syml.types import Source


class TestTextOnlySymlParser:
    @pytest.fixture
    def parser(self):
        return parser.TextOnlySymlParser()

    def test_it_should_parse_a_simple_text_value(self, parser):
        text = textwrap.dedent("true")
        result = parser.parse(text)
        assert result.as_data() == Source.from_text(text, "true")

    def test_it_should_parse_a_simple_multiline_list(self, parser):
        text = textwrap.dedent(
            """
            - foo
            - bar
            - baz
            """
        )
        result = parser.parse(text)
        assert result.as_data() == [
            Source.from_text(text, "foo"),
            Source.from_text(text, "bar"),
            Source.from_text(text, "baz"),
        ]

    def test_it_should_parse_a_simple_single_line_list(self, parser):
        text = textwrap.dedent(
            """
            - foo
            """
        )
        result = parser.parse(text)
        assert result.as_data() == [
            Source.from_text(text, "foo"),
        ]

    def test_it_should_parse_a_list_with_multiline_values(self, parser):
        text = textwrap.dedent(
            """
            - foo
            - bar
              baz
            """
        )
        result = parser.parse(text)
        assert result.as_data() == [
            Source.from_text(text, "foo"),
            Source.from_text(text, "bar\n  baz", "bar\nbaz", "bar\nbaz"),
        ]

    def test_it_should_parse_a_list_with_embedded_mappings_values(self, parser):
        text = textwrap.dedent(
            """
            - foo:
                bar
            - baz: boo
              blah:
                baloon
            """
        )
        result = parser.parse(text)
        assert result.as_data() == [
            {Source.from_text(text, "foo"): Source.from_text(text, "bar")},
            {
                Source.from_text(text, "baz"): Source.from_text(text, "boo"),
                Source.from_text(text, "blah"): Source.from_text(text, "baloon"),
            },
        ]

    def test_it_should_parse_a_simple_single_line_mapping(self, parser):
        text = textwrap.dedent(
            """
            foo: bar
            """
        )
        result = parser.parse(text)
        assert result.as_data() == OrderedDict(
            [
                (Source.from_text(text, "foo"), Source.from_text(text, "bar")),
            ]
        )

    def test_it_should_parse_a_simple_multiline_mapping(self, parser):
        text = textwrap.dedent(
            """
            foo: bar
            baz: boo
            """
        )
        result = parser.parse(text)
        assert result.as_data() == OrderedDict(
            [
                (Source.from_text(text, "foo"), Source.from_text(text, "bar")),
                (Source.from_text(text, "baz"), Source.from_text(text, "boo")),
            ]
        )

    def test_it_should_parse_a_weirdly_nested_mapping(self, parser):
        text = textwrap.dedent(
            """
            foo: bar: blah
            baz: boo
            """
        )
        result = parser.parse(text)
        assert result.as_data() == OrderedDict(
            [
                (Source.from_text(text, "foo"), Source.from_text(text, "bar: blah")),
                (Source.from_text(text, "baz"), Source.from_text(text, "boo")),
            ]
        )

    def test_it_should_parse_a_nested_mapping_with_list(self, parser):
        text = textwrap.dedent(
            """
            foo:
              - bar
              - baz
            blah: boo
            """
        )
        result = parser.parse(text)
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

    def test_it_should_parse_a_nested_mapping_with_weirdly_nested_list(self, parser):
        text = textwrap.dedent(
            """
            foo: - bar
            blah: boo
            """
        )
        result = parser.parse(text)
        assert result.as_data() == OrderedDict(
            [
                (Source.from_text(text, "foo"), Source.from_text(text, "- bar")),
                (Source.from_text(text, "blah"), Source.from_text(text, "boo")),
            ]
        )

    def test_it_should_parse_a_nested_list_with_mapping(self, parser):
        text = textwrap.dedent(
            """
            - foo:
              - bar
              - baz
            - blah: boo
            """
        )
        result = parser.parse(text)
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

    def test_it_should_parse_comments_and_blanks(self, parser):
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
        result = parser.parse(text)
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

    def test_it_fails_parsing_weird_indentations(self, parser):
        bad_yaml = textwrap.dedent(
            """
              - foo:
                  - bar
             - baz
            - blah
            """
        )
        with pytest.raises(exceptions.OutOfContextNodeError):
            parser.parse(bad_yaml)


class TestBooleanSymlParser:
    @pytest.fixture
    def parser(self):
        return parser.BooleanSymlParser()

    def test_it_should_parse_a_simple_boolean_value(self, parser):
        text = textwrap.dedent("true")
        result = parser.parse(text)
        assert result.as_data() == Source.from_text(text, "true", value=True)

    def test_it_should_parse_mixed_boolean_values(self, parser):
        text = textwrap.dedent(
            """
            - foo
            - true
            - false
            """
        )
        result = parser.parse(text)
        assert result.as_data() == [
            Source.from_text(text, "foo"),
            Source.from_text(text, "true", value=True),
            Source.from_text(text, "false", value=False),
        ]


class TestSimpleParserFunction:
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
