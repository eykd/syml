import textwrap
from io import StringIO

import pytest

import syml
from syml import exceptions, parsers
from syml.basetypes import Source


class TestSymlParser:
    @pytest.fixture
    def parser(self) -> parsers.SymlParser:
        return parsers.SymlParser()

    def test_it_should_parse_a_simple_text_value(self, parser: parsers.SymlParser) -> None:
        text = textwrap.dedent('true')
        result = parser.parse(text)
        assert result.as_data() == 'true'
        assert result.as_source() == Source.from_text('true', 'true')

    def test_it_should_parse_a_simple_multiline_list(self, parser: parsers.SymlParser) -> None:
        text = textwrap.dedent(
            """
            - foo
            - bar
            - baz
            """
        )
        result = parser.parse(text)
        expected = ['foo', 'bar', 'baz']
        assert result.as_data() == expected
        assert result.as_source() == [
            Source.from_text(text, 'foo'),
            Source.from_text(text, 'bar'),
            Source.from_text(text, 'baz'),
        ]

    def test_it_should_parse_a_simple_single_line_list(self, parser: parsers.SymlParser) -> None:
        text = textwrap.dedent(
            """
            - foo
            """
        )
        result = parser.parse(text)
        assert result.as_data() == ['foo']
        assert result.as_source() == [
            Source.from_text(text, 'foo'),
        ]

    def test_it_should_parse_a_list_with_multiline_values(self, parser: parsers.SymlParser) -> None:
        text = textwrap.dedent(
            """
            - foo
            - bar
              baz
            """
        )
        result = parser.parse(text)
        expected = ['foo', 'bar\nbaz']
        assert result.as_data() == expected
        assert result.as_source() == [
            Source.from_text(text, 'foo'),
            Source.from_text(text, 'bar\n  baz', 'bar\nbaz'),
        ]

    def test_it_should_parse_a_list_with_embedded_mappings_values(self, parser: parsers.SymlParser) -> None:
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
        expected = [
            {'foo': 'bar'},
            {'baz': 'boo', 'blah': 'baloon'},
        ]
        assert result.as_data() == expected
        assert result.as_source() == [
            {Source.from_text(text, 'foo'): Source.from_text(text, 'bar')},
            {
                Source.from_text(text, 'baz'): Source.from_text(text, 'boo'),
                Source.from_text(text, 'blah'): Source.from_text(text, 'baloon'),
            },
        ]

    def test_it_should_parse_a_simple_single_line_mapping(self, parser: parsers.SymlParser) -> None:
        text = textwrap.dedent(
            """
            foo: bar
            """
        )
        result = parser.parse(text)
        assert result.as_data() == {'foo': 'bar'}
        assert result.as_source() == {Source.from_text(text, 'foo'): Source.from_text(text, 'bar')}

    def test_it_should_parse_a_simple_multiline_mapping(self, parser: parsers.SymlParser) -> None:
        text = textwrap.dedent(
            """
            foo: bar
            baz: boo
            """
        )
        result = parser.parse(text)
        expected = {'foo': 'bar', 'baz': 'boo'}
        assert result.as_data() == expected
        assert result.as_source() == {
            Source.from_text(text, 'foo'): Source.from_text(text, 'bar'),
            Source.from_text(text, 'baz'): Source.from_text(text, 'boo'),
        }

    def test_it_should_parse_a_weirdly_nested_mapping(self, parser: parsers.SymlParser) -> None:
        text = textwrap.dedent(
            """
            foo: bar: blah
            baz: boo
            """
        )
        result = parser.parse(text)
        expected = {'foo': 'bar: blah', 'baz': 'boo'}
        assert result.as_data() == expected
        assert result.as_source() == {
            Source.from_text(text, 'foo'): Source.from_text(text, 'bar: blah'),
            Source.from_text(text, 'baz'): Source.from_text(text, 'boo'),
        }

    def test_it_should_parse_a_nested_mapping_with_list(self, parser: parsers.SymlParser) -> None:
        text = textwrap.dedent(
            """
            foo:
              - bar
              - baz
            blah: boo
            """
        )
        result = parser.parse(text)
        expected = {'blah': 'boo', 'foo': ['bar', 'baz']}
        assert result.as_data() == expected
        assert result.as_source() == {
            Source.from_text(text, 'foo'): [Source.from_text(text, 'bar'), Source.from_text(text, 'baz')],
            Source.from_text(text, 'blah'): Source.from_text(text, 'boo'),
        }

    def test_it_should_parse_a_nested_mapping_with_weirdly_nested_list(self, parser: parsers.SymlParser) -> None:
        text = textwrap.dedent(
            """
            foo: - bar
            blah: boo
            """
        )
        result = parser.parse(text)
        expected = {'foo': '- bar', 'blah': 'boo'}
        assert result.as_data() == expected
        assert result.as_source() == {
            Source.from_text(text, 'foo'): Source.from_text(text, '- bar'),
            Source.from_text(text, 'blah'): Source.from_text(text, 'boo'),
        }

    def test_it_should_parse_a_nested_list_with_mapping(self, parser: parsers.SymlParser) -> None:
        text = textwrap.dedent(
            """
            - foo:
              - bar
              - baz
            - blah: boo
            """
        )
        result = parser.parse(text)
        expected = [
            {'foo': ['bar', 'baz']},
            {'blah': 'boo'},
        ]
        assert result.as_data() == expected
        assert result.as_source() == [
            {
                Source.from_text(text, 'foo'): [Source.from_text(text, 'bar'), Source.from_text(text, 'baz')],
            },
            {
                Source.from_text(text, 'blah'): Source.from_text(text, 'boo'),
            },
        ]

    def test_it_should_parse_comments_and_blanks(self, parser: parsers.SymlParser) -> None:
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
        expected = [{'foo': ['bar', 'baz']}, {'blah': 'boo # not a comment!'}]
        assert result.as_data() == expected
        assert result.as_source() == [
            {
                Source.from_text(text, 'foo'): [Source.from_text(text, 'bar'), Source.from_text(text, 'baz')],
            },
            {
                Source.from_text(text, 'blah'): Source.from_text(text, 'boo # not a comment!'),
            },
        ]

    def test_it_fails_parsing_weird_indentations(self, parser: parsers.SymlParser) -> None:
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


class TestSimpleParserFunction:
    def test_it_should_parse_a_simple_list(self) -> None:
        text = textwrap.dedent(
            """
            - foo
            - true
            - false
            """
        )
        result = parsers.parse(text)
        assert result == [
            'foo',
            'true',
            'false',
        ]

    def test_it_should_parse_whats_in_the_readme_text_only(self) -> None:
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
            'foo': [
                'bar',
                'baz',
                'blah\nboo\nbaloon',
            ],
            'booleans?': [
                'True',
                'False',
                'true',
                'false',
                'TRUE',
                'FALSE',
            ],
        }

    def test_it_should_parse_whats_in_the_readme_text_only_from_a_fileobj(self) -> None:
        buf = StringIO(
            textwrap.dedent(
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
        )
        result = syml.load(buf)
        assert result == {
            'foo': [
                'bar',
                'baz',
                'blah\nboo\nbaloon',
            ],
            'booleans?': [
                'True',
                'False',
                'true',
                'false',
                'TRUE',
                'FALSE',
            ],
        }
