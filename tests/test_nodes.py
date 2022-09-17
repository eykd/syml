# -*- coding: utf-8 -*-
from unittest import TestCase
from unittest.mock import Mock

import ensure

from syml import exceptions
from syml import nodes

ensure = ensure.ensure


class YamlNodeTests(TestCase):
    def setUp(self):
        self.node = nodes.YamlNode(Mock())

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
        self.root = nodes.Root(Mock())

    def test_it_should_add_a_list(self):
        new_node = nodes.List(Mock(), level=4)
        result = self.root.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.root.value).is_(new_node)
        ensure(new_node.parent).is_(self.root)

    def test_it_should_add_a_list_item_and_create_an_intervening_list(self):
        new_node = nodes.ListItem(Mock(), 'foo', level=4)
        result = self.root.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.root.value).is_an(nodes.List)

        ensure(result.parent).is_(self.root.value)
        ensure(self.root.value.parent).is_(self.root)

    def test_it_should_add_a_keyvalue_and_create_an_intervening_mapping(self):
        new_node = nodes.KeyValue(Mock(), 'foo', value='bar', level=4)
        result = self.root.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.root.value).is_an(nodes.Mapping)

        ensure(result.parent).is_(self.root.value)
        ensure(self.root.value.parent).is_(self.root)


class ListTests(TestCase):
    def setUp(self):
        self.root = nodes.Root(Mock())
        self.node = self.root.add_node(nodes.List(Mock()))
        self.node.level = 4

    def test_it_should_add_a_list_item_at_a_higher_level(self):
        new_node = nodes.ListItem(Mock(), value='foo', level=8)
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
        new_node = nodes.ListItem(pnode, value='foo', level=3)
        (ensure(self.node.incorporate_node)
         .called_with(new_node)
         .raises(exceptions.OutOfContextNodeError)
         )

    def test_it_should_not_add_a_keyvalue_item_at_a_higher_level(self):
        pnode = Mock(
            full_text = '    - bar\n     foo: baz',
            text = 'foo: baz',
            start = 18,
        )
        new_node = nodes.KeyValue(pnode, key='foo', value='bar', level=8)
        (ensure(self.node.incorporate_node)
         .called_with(new_node)
         .raises(exceptions.OutOfContextNodeError)
         )


class MappingTests(TestCase):
    def setUp(self):
        self.root = nodes.Root(Mock())
        self.node = self.root.add_node(nodes.Mapping(Mock()))
        self.node.level = 4

    def test_it_should_add_a_keyvalue_at_a_higher_level(self):
        new_node = nodes.KeyValue(Mock(), 'foo', value='bar', level=8)
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
        new_node = nodes.KeyValue(pnode, 'foo', value='bar', level=3)
        (ensure(self.node.incorporate_node)
         .called_with(new_node)
         .raises(exceptions.OutOfContextNodeError)
         )

    def test_it_should_not_add_a_listitem_at_a_higher_level(self):
        pnode = Mock(
            full_text = '    foo: bar\n       - baz',
            text = '- baz',
            start = 18,
        )
        new_node = nodes.ListItem(pnode, value='foo', level=8)
        (ensure(self.node.incorporate_node)
         .called_with(new_node)
         .raises(exceptions.OutOfContextNodeError)
         )


class ListItemTests(TestCase):
    def setUp(self):
        self.root = nodes.Root(Mock())
        self.level = 4
        self.node = self.root.incorporate_node(nodes.ListItem(Mock(), level=self.level))

    def test_it_should_add_a_list_at_a_higher_level(self):
        new_node = nodes.List(Mock(), level=self.level + 4)
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_(new_node)
        ensure(new_node.parent).is_(self.node)

    def test_it_should_add_a_list_item_at_a_higher_level_and_create_an_intervening_list(self):
        new_node = nodes.ListItem(Mock(), 'foo', level=self.level + 4)
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_an(nodes.List)
        ensure(self.node.value.level).equals(new_node.level)

        ensure(result.parent).is_(self.node.value)
        ensure(self.node.value.parent).is_(self.node)

    def test_it_should_cooperatively_add_a_list_item_at_the_same_level_to_the_parent_list(self):
        new_node = nodes.ListItem(Mock(), 'foo', level=self.level)
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_none()
        ensure(self.node.parent.children).has_length(2)
        ensure(self.node.parent.children[-1]).is_(new_node)

        ensure(new_node.parent).is_(self.node.parent)

    def test_it_should_add_a_keyvalue_at_a_higher_level_and_create_an_intervening_mapping(self):
        new_node = nodes.KeyValue(Mock(), 'foo', value='bar', level=self.level + 4)
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_an(nodes.Mapping)
        ensure(self.node.value.level).equals(new_node.level)

        ensure(result.parent).is_(self.node.value)
        ensure(self.node.value.parent).is_(self.node)

    def test_it_should_add_a_keyvalue_with_no_level_and_create_an_intervening_mapping(self):
        new_node = nodes.KeyValue(Mock(), 'foo', value='bar', level=None)
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_an(nodes.Mapping)
        ensure(self.node.value.level).equals(new_node.level)

        ensure(result.parent).is_(self.node.value)
        ensure(self.node.value.parent).is_(self.node)

    def test_it_should_add_a_leafnode(self):
        new_node = nodes.LeafNode(Mock(), 'foo')
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_(new_node)
        ensure(new_node.parent).is_(self.node)


class KeyValueTests(TestCase):
    def setUp(self):
        self.root = nodes.Root(Mock())
        self.level = 4
        self.node = self.root.incorporate_node(
            nodes.KeyValue(Mock(), 'foo', level=self.level)
        )

    def test_it_should_add_a_list_at_a_higher_level(self):
        new_node = nodes.List(Mock(), level=self.level + 4)
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_(new_node)
        ensure(new_node.parent).is_(self.node)

    def test_it_should_add_a_list_item_at_a_higher_level_and_create_an_intervening_list(self):
        new_node = nodes.ListItem(Mock(), 'foo', level=self.level + 4)
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_an(nodes.List)
        ensure(self.node.value.level).equals(new_node.level)

        ensure(result.parent).is_(self.node.value)
        ensure(self.node.value.parent).is_(self.node)

    def test_it_should_cooperatively_add_a_keyvalue_at_the_same_level_to_the_parent_mapping(self):
        new_node = nodes.KeyValue(Mock(), 'bar', level=self.level)
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_none()
        ensure(self.node.parent.children).has_length(2)
        ensure(self.node.parent.children[-1]).is_(new_node)

        ensure(new_node.parent).is_(self.node.parent)

    def test_it_should_add_a_keyvalue_at_a_higher_level_and_create_an_intervening_mapping(self):
        new_node = nodes.KeyValue(Mock(), 'foo', value='bar', level=self.level + 4)
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_an(nodes.Mapping)
        ensure(self.node.value.level).equals(new_node.level)

        ensure(result.parent).is_(self.node.value)
        ensure(self.node.value.parent).is_(self.node)

    def test_it_should_add_a_leafnode(self):
        new_node = nodes.LeafNode(Mock(), 'foo')
        result = self.node.incorporate_node(new_node)
        ensure(result).is_(new_node)
        ensure(self.node.value).is_(new_node)
        ensure(new_node.parent).is_(self.node)
