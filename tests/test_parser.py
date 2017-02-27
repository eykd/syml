# -*- coding: utf-8 -*-
from collections import OrderedDict
from unittest import TestCase
from unittest.mock import Mock
import textwrap

import ensure

from syml import exceptions
from syml import parser
from syml.utils import get_text_source

ensure.unittest_case.maxDiff = None

ensure = ensure.ensure


class YamlNodeTests(TestCase):
    def setUp(self):
        self.node = parser.YamlNode(Mock())

    def test_as_data_is_not_implemented(self):
        (ensure(self.node.as_data)
         .called_with('foo.txt')
         .raises(NotImplementedError)
         )

    def test_add_node_is_not_implemented(self):
        (ensure(self.node.add_node)
         .called_with(Mock())
         .raises(NotImplementedError)
         )

    def test_it_cant_add_a_node(self):
        (ensure(self.node.can_add_node)
         .called_with(Mock())
         .is_false()
         )


class RootTests(TestCase):
    def setUp(self):
        self.root = parser.Root(Mock())

    def test_it_should_add_a_list(self):
        new_node = parser.List(Mock(), level=4)
        result = self.root.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.root.value).is_(new_node)
        ensure(new_node.parent).is_(self.root)

    def test_it_should_add_a_list_item_and_create_an_intervening_list(self):
        new_node = parser.ListItem(Mock(), 'foo', level=4)
        result = self.root.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.root.value).is_an(parser.List)

        ensure(result.parent).is_(self.root.value)
        ensure(self.root.value.parent).is_(self.root)

    def test_it_should_add_a_keyvalue_and_create_an_intervening_mapping(self):
        new_node = parser.KeyValue(Mock(), 'foo', value='bar', level=4)
        result = self.root.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.root.value).is_an(parser.Mapping)

        ensure(result.parent).is_(self.root.value)
        ensure(self.root.value.parent).is_(self.root)


class ListTests(TestCase):
    def setUp(self):
        self.root = parser.Root(Mock())
        self.node = self.root.add_node(parser.List(Mock()))
        self.node.level = 4

    def test_it_should_add_a_list_item_at_a_higher_level(self):
        new_node = parser.ListItem(Mock(), value='foo', level=8)
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(result.parent).is_(self.node)
        ensure(self.node.children).contains(new_node)

    def test_it_should_not_add_a_list_item_at_a_lower_level(self):
        pnode = Mock(
            full_text = '    - bar\n   - foo',
            text = '- foo',
            start = 16,
        )
        new_node = parser.ListItem(pnode, value='foo', level=3)
        (ensure(self.node.incorporate_node)
         .called_with(new_node)
         .raises(parser.OutOfContextNodeError)
         )

    def test_it_should_not_add_a_keyvalue_item_at_a_higher_level(self):
        pnode = Mock(
            full_text = '    - bar\n     foo: baz',
            text = 'foo: baz',
            start = 18,
        )
        new_node = parser.KeyValue(pnode, key='foo', value='bar', level=8)
        (ensure(self.node.incorporate_node)
         .called_with(new_node)
         .raises(parser.OutOfContextNodeError)
         )


class MappingTests(TestCase):
    def setUp(self):
        self.root = parser.Root(Mock())
        self.node = self.root.add_node(parser.Mapping(Mock()))
        self.node.level = 4

    def test_it_should_add_a_keyvalue_at_a_higher_level(self):
        new_node = parser.KeyValue(Mock(), 'foo', value='bar', level=8)
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(result.parent).is_(self.node)
        ensure(self.node.children).contains(new_node)

    def test_it_should_not_add_a_keyvalue_at_a_lower_level(self):
        pnode = Mock(
            full_text = '    foo: bar\n   bar: baz',
            text = 'bar: baz',
            start = 14,
        )
        new_node = parser.KeyValue(pnode, 'foo', value='bar', level=3)
        (ensure(self.node.incorporate_node)
         .called_with(new_node)
         .raises(parser.OutOfContextNodeError)
         )

    def test_it_should_not_add_a_listitem_at_a_higher_level(self):
        pnode = Mock(
            full_text = '    foo: bar\n       - baz',
            text = '- baz',
            start = 18,
        )
        new_node = parser.ListItem(pnode, value='foo', level=8)
        (ensure(self.node.incorporate_node)
         .called_with(new_node)
         .raises(parser.OutOfContextNodeError)
         )


class ListItemTests(TestCase):
    def setUp(self):
        self.root = parser.Root(Mock())
        self.level = 4
        self.node = self.root.incorporate_node(parser.ListItem(Mock(), level=self.level))

    def test_it_should_add_a_list_at_a_higher_level(self):
        new_node = parser.List(Mock(), level=self.level + 4)
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_(new_node)
        ensure(new_node.parent).is_(self.node)

    def test_it_should_add_a_list_item_at_a_higher_level_and_create_an_intervening_list(self):
        new_node = parser.ListItem(Mock(), 'foo', level=self.level + 4)
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_an(parser.List)
        ensure(self.node.value.level).equals(new_node.level)

        ensure(result.parent).is_(self.node.value)
        ensure(self.node.value.parent).is_(self.node)

    def test_it_should_cooperatively_add_a_list_item_at_the_same_level_to_the_parent_list(self):
        new_node = parser.ListItem(Mock(), 'foo', level=self.level)
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_none()
        ensure(self.node.parent.children).has_length(2)
        ensure(self.node.parent.children[-1]).is_(new_node)

        ensure(new_node.parent).is_(self.node.parent)

    def test_it_should_add_a_keyvalue_at_a_higher_level_and_create_an_intervening_mapping(self):
        new_node = parser.KeyValue(Mock(), 'foo', value='bar', level=self.level + 4)
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_an(parser.Mapping)
        ensure(self.node.value.level).equals(new_node.level)

        ensure(result.parent).is_(self.node.value)
        ensure(self.node.value.parent).is_(self.node)

    def test_it_should_add_a_keyvalue_with_no_level_and_create_an_intervening_mapping(self):
        new_node = parser.KeyValue(Mock(), 'foo', value='bar', level=None)
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_an(parser.Mapping)
        ensure(self.node.value.level).equals(new_node.level)

        ensure(result.parent).is_(self.node.value)
        ensure(self.node.value.parent).is_(self.node)

    def test_it_should_add_a_leafnode(self):
        new_node = parser.LeafNode(Mock(), 'foo')
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_(new_node)
        ensure(new_node.parent).is_(self.node)


class KeyValueTests(TestCase):
    def setUp(self):
        self.root = parser.Root(Mock())
        self.level = 4
        self.node = self.root.incorporate_node(
            parser.KeyValue(Mock(), 'foo', level=self.level)
        )

    def test_it_should_add_a_list_at_a_higher_level(self):
        new_node = parser.List(Mock(), level=self.level + 4)
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_(new_node)
        ensure(new_node.parent).is_(self.node)

    def test_it_should_add_a_list_item_at_a_higher_level_and_create_an_intervening_list(self):
        new_node = parser.ListItem(Mock(), 'foo', level=self.level + 4)
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_an(parser.List)
        ensure(self.node.value.level).equals(new_node.level)

        ensure(result.parent).is_(self.node.value)
        ensure(self.node.value.parent).is_(self.node)

    def test_it_should_cooperatively_add_a_keyvalue_at_the_same_level_to_the_parent_mapping(self):
        new_node = parser.KeyValue(Mock(), 'bar', level=self.level)
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_none()
        ensure(self.node.parent.children).has_length(2)
        ensure(self.node.parent.children[-1]).is_(new_node)

        ensure(new_node.parent).is_(self.node.parent)

    def test_it_should_add_a_keyvalue_at_a_higher_level_and_create_an_intervening_mapping(self):
        new_node = parser.KeyValue(Mock(), 'foo', value='bar', level=self.level + 4)
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_an(parser.Mapping)
        ensure(self.node.value.level).equals(new_node.level)

        ensure(result.parent).is_(self.node.value)
        ensure(self.node.value.parent).is_(self.node)

    def test_it_should_add_a_leafnode(self):
        new_node = parser.LeafNode(Mock(), 'foo')
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_(new_node)
        ensure(new_node.parent).is_(self.node)


class TextOnlySlymlParserTests(TestCase):
    def setUp(self):
        self.parser = parser.TextOnlySlymlParser()

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


class BooleanSlymlParserTests(TestCase):
    def setUp(self):
        self.parser = parser.BooleanSlymlParser()

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
