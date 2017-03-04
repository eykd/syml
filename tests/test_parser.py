# -*- coding: utf-8 -*-
from collections import OrderedDict
from unittest import TestCase
import textwrap

import ensure

from syml import exceptions
from syml import parser
from syml.utils import get_text_source

ensure.unittest_case.maxDiff = None

ensure = ensure.ensure


class TextOnlySymlParserTests(TestCase):
    def setUp(self):
        self.parser = parser.TextOnlySymlParser()

    def test_it_should_parse_a_simple_text_value(self):
        text = textwrap.dedent("yes")
        result = self.parser.parse(text)
        ensure(result.as_data()).equals(
            get_text_source(text, 'yes'),
        )

    def test_it_should_parse_a_simple_list(self):
        text = textwrap.dedent("""
            - foo
            - bar
            - baz
        """)
        result = self.parser.parse(text)
        ensure(result.as_data()).equals([
            get_text_source(text, 'foo'),
            get_text_source(text, 'bar'),
            get_text_source(text, 'baz'),
        ])

    def test_it_should_parse_a_list_with_multiline_values(self):
        text = textwrap.dedent("""
            - foo
            - bar
              baz
        """)
        result = self.parser.parse(text)
        ensure(result.as_data()).equals([
            get_text_source(text, 'foo'),
            get_text_source(text, 'bar\n  baz', 'bar', 'bar\nbaz')
        ])

    def test_it_should_parse_a_list_with_embedded_mappings_values(self):
        text = textwrap.dedent("""
            - foo:
                bar
            - baz: boo
              blah:
                baloon
        """)
        result = self.parser.parse(text)
        ensure(result.as_data()).equals([
            {get_text_source(text, 'foo'): get_text_source(text, 'bar')},
            {get_text_source(text, 'baz'): get_text_source(text, 'boo'),
             get_text_source(text, 'blah'): get_text_source(text, 'baloon')},
        ])

    def test_it_should_parse_a_simple_mapping(self):
        text = textwrap.dedent("""
            foo: bar
            baz: boo
        """)
        result = self.parser.parse(text)
        ensure(result.as_data()).equals(OrderedDict([
            (get_text_source(text, 'foo'), get_text_source(text, 'bar')),
            (get_text_source(text, 'baz'), get_text_source(text, 'boo')),
        ]))

    def test_it_should_parse_a_weirdly_nested_mapping(self):
        text = textwrap.dedent("""
            foo: bar: blah
            baz: boo
        """)
        result = self.parser.parse(text)
        ensure(result.as_data()).equals(OrderedDict([
            (get_text_source(text, 'foo'), get_text_source(text, 'bar: blah')),
            (get_text_source(text, 'baz'), get_text_source(text, 'boo')),
        ]))

    def test_it_should_parse_a_nested_mapping_with_list(self):
        text = textwrap.dedent("""
            foo:
              - bar
              - baz
            blah: boo
        """)
        result = self.parser.parse(text)
        ensure(result.as_data()).equals(OrderedDict([
            (get_text_source(text, 'foo'), [
                get_text_source(text, 'bar'),
                get_text_source(text, 'baz'),
            ]),
            (get_text_source(text, 'blah'), get_text_source(text, 'boo')),
        ]))

    def test_it_should_parse_a_nested_mapping_with_weirdly_nested_list(self):
        text = textwrap.dedent("""
            foo: - bar
            blah: boo
        """)
        result = self.parser.parse(text)
        ensure(result.as_data()).equals(OrderedDict([
            (get_text_source(text, 'foo'), get_text_source(text, '- bar')),
            (get_text_source(text, 'blah'), get_text_source(text, 'boo')),
        ]))

    def test_it_should_parse_a_nested_list_with_mapping(self):
        text = textwrap.dedent("""
            - foo:
              - bar
              - baz
            - blah: boo
        """)
        result = self.parser.parse(text)
        ensure(result.as_data()).equals([
            OrderedDict([
                (get_text_source(text, 'foo'), [
                    get_text_source(text, 'bar'),
                    get_text_source(text, 'baz'),
                ]),
            ]),
            OrderedDict([
                (get_text_source(text, 'blah'), get_text_source(text, 'boo')),
            ]),
        ])

    def test_it_should_parse_comments_and_blanks(self):
        text = textwrap.dedent("""
        # A comment
        - foo:

          - bar
          # Something else entirely
          - baz

        - blah: boo # not a comment!

        """)
        result = self.parser.parse(text)
        ensure(result.as_data()).equals([
            OrderedDict([
                (get_text_source(text, 'foo'), [
                    get_text_source(text, 'bar'),
                    get_text_source(text, 'baz'),
                ]),
            ]),
            OrderedDict([
                (get_text_source(text, 'blah'),
                 get_text_source(text, 'boo # not a comment!'))
            ]),
        ])

    def test_it_fails_parsing_weird_indentations(self):
        bad_yaml = textwrap.dedent("""
          - foo:
              - bar
         - baz
        - blah
        """)
        (ensure(self.parser.parse)
         .called_with(bad_yaml)
         .raises(exceptions.OutOfContextNodeError)
         )


class BooleanSymlParserTests(TestCase):
    def setUp(self):
        self.parser = parser.BooleanSymlParser()

    def test_it_should_parse_a_simple_boolean_value(self):
        text = textwrap.dedent("yes")
        result = self.parser.parse(text)
        ensure(result.as_data()).equals(
            get_text_source(text, 'yes', value=True),
        )

    def test_it_should_parse_mixed_boolean_values(self):
        text = textwrap.dedent("""
            - foo
            - yes
            - false
        """)
        result = self.parser.parse(text)
        ensure(result.as_data()).equals([
            get_text_source(text, 'foo'),
            get_text_source(text, 'yes', value=True),
            get_text_source(text, 'false', value=False),
        ])


class SimpleParserFunctionTests(TestCase):
    def test_it_should_parse_a_simple_list(self):
        text = textwrap.dedent("""
            - foo
            - yes
            - false
        """)
        result = parser.parse(text)
        ensure(result).equals([
            'foo',
            'yes',
            'false',
        ])

    def test_it_should_parse_whats_in_the_readme(self):
        text = textwrap.dedent("""
            foo:
              - bar
              - baz
              - blah
                boo

            booleans?:
              - yes
              - no
        """)
        result = parser.parse(text)
        ensure(result).equals({
            'foo': [
                'bar',
                'baz',
                'blah\nboo',
            ],
            'booleans?': [
                'yes',
                'no',
            ]
        })
