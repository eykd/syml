from unittest.mock import Mock

import pytest

from syml import basetypes, exceptions, nodes


@pytest.fixture
def level() -> int:
    return 4


@pytest.fixture
def root() -> nodes.Root:
    return nodes.Root(pnode=Mock())


class TestRoot:
    def test_it_should_add_a_list(self, root: nodes.Root, level: int) -> None:
        new_node = nodes.List(pnode=Mock(), level=level)
        result = root.incorporate_node(new_node)
        assert result is new_node
        assert root.value is new_node
        assert new_node.parent is root
        assert root.get_tip() is new_node

    def test_it_should_add_a_list_item_and_create_an_intervening_list(self, root: nodes.Root, level: int) -> None:
        new_node = nodes.ListItem(pnode=Mock(), value='foo', level=level)
        result = root.incorporate_node(new_node)
        assert result is new_node
        assert isinstance(root.value, nodes.List)

        assert result.parent is root.value
        assert root.value.parent is root
        assert root.get_tip() is new_node

    def test_it_should_add_a_keyvalue_and_create_an_intervening_mapping(self, root: nodes.Root, level: int) -> None:
        new_node = nodes.KeyValue(pnode=Mock(), key='foo', value='bar', level=level)
        result = root.incorporate_node(new_node)
        assert result is new_node
        assert isinstance(root.value, nodes.Mapping)

        assert result.parent is root.value
        assert root.value.parent is root
        assert root.get_tip() is new_node


class TestList:
    @pytest.fixture
    def node(self, root: nodes.Root, level: int) -> nodes.List:
        node = nodes.List(pnode=Mock())
        root.add_node(node)
        node.level = level
        return node

    def test_it_should_add_a_list_item_at_a_higher_level(self, node: nodes.List, level: int) -> None:
        new_node = nodes.ListItem(pnode=Mock(), value='foo', level=level + 4)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert result.parent is node
        assert new_node in node.children
        assert node.get_tip() is new_node

    def test_it_should_not_add_a_list_item_at_a_lower_level(self, node: nodes.List, level: int) -> None:
        pnode = Mock(
            full_text='    - bar\n   - foo',
            text='- foo',
            start=16,
        )
        new_node = nodes.ListItem(pnode=pnode, value='foo', level=level - 1)
        with pytest.raises(exceptions.OutOfContextNodeError):
            node.incorporate_node(new_node)

    def test_it_should_not_add_a_keyvalue_item_at_a_higher_level(self, node: nodes.List, level: int) -> None:
        pnode = Mock(
            full_text='    - bar\n     foo: baz',
            text='foo: baz',
            start=level + 4,
        )
        new_node = nodes.KeyValue(pnode=pnode, key='foo', value='bar', level=level + 4)
        with pytest.raises(exceptions.OutOfContextNodeError):
            node.incorporate_node(new_node)


class TestMapping:
    @pytest.fixture
    def node(self, root: nodes.Root, level: int) -> nodes.Mapping:
        node = nodes.Mapping(pnode=Mock())
        root.add_node(node)
        node.level = level
        return node

    def test_it_should_add_a_keyvalue_at_a_higher_level(self, node: nodes.Mapping, level: int) -> None:
        new_node = nodes.KeyValue(pnode=Mock(), key='foo', value='bar', level=level + 4)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert result.parent is node
        assert new_node in node.children
        assert node.get_tip() is new_node

    def test_it_should_not_add_a_keyvalue_at_a_lower_level(self, node: nodes.Mapping, level: int) -> None:
        pnode = Mock(
            full_text='    foo: bar\n   bar: baz',
            text='bar: baz',
            start=14,
        )
        new_node = nodes.KeyValue(pnode=pnode, key='foo', value='bar', level=level - 1)
        with pytest.raises(exceptions.OutOfContextNodeError):
            node.incorporate_node(new_node)

    def test_it_should_not_add_a_listitem_at_a_higher_level(self, node: nodes.Mapping, level: int) -> None:
        pnode = Mock(
            full_text='    foo: bar\n       - baz',
            text='- baz',
            start=level + 4,
        )
        new_node = nodes.ListItem(pnode=pnode, value='foo', level=level + 4)
        with pytest.raises(exceptions.OutOfContextNodeError):
            node.incorporate_node(new_node)


class TestListItem:
    @pytest.fixture
    def node(self, root: nodes.Root, level: int) -> nodes.ListItem:
        node = nodes.ListItem(pnode=Mock(), level=level)
        root.incorporate_node(node)
        return node

    def test_it_should_add_a_list_at_a_higher_level(self, node: nodes.ListItem, level: int) -> None:
        new_node = nodes.List(pnode=Mock(), level=level + 4)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert node.value is new_node
        assert new_node.parent is node
        assert node.get_tip() is new_node

    def test_it_should_add_a_list_item_at_a_higher_level_and_create_an_intervening_list(
        self, node: nodes.ListItem, level: int
    ) -> None:
        new_node = nodes.ListItem(pnode=Mock(), value='foo', level=level + 4)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert isinstance(node.value, nodes.List)
        assert node.value.level == new_node.level

        assert result.parent is node.value
        assert node.value.parent is node
        assert node.get_tip() is new_node

    def test_it_should_cooperatively_add_a_list_item_at_the_same_level_to_the_parent_list(
        self, node: nodes.ListItem, level: int
    ) -> None:
        new_node = nodes.ListItem(pnode=Mock(), value='foo', level=level)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert node.value is None
        assert node.parent is not None
        assert len(node.parent.children) == 2
        assert node.parent.children[-1] is new_node

        assert new_node.parent is node.parent
        assert node.get_tip() is node
        assert node.parent.get_tip() is new_node

    def test_it_should_add_a_keyvalue_at_a_higher_level_and_create_an_intervening_mapping(
        self, node: nodes.ListItem, level: int
    ) -> None:
        new_node = nodes.KeyValue(pnode=Mock(), key='foo', value='bar', level=level + 4)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert isinstance(node.value, nodes.Mapping)
        assert node.value.level == new_node.level

        assert result.parent is node.value
        assert node.value.parent is node
        assert node.get_tip() is new_node

    def test_it_should_add_a_keyvalue_with_no_level_and_create_an_intervening_mapping(
        self, node: nodes.ListItem
    ) -> None:
        new_node = nodes.KeyValue(pnode=Mock(), key='foo', value='bar', level=None)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert isinstance(node.value, nodes.Mapping)
        assert node.value.level == new_node.level

        assert result.parent is node.value
        assert node.value.parent is node
        assert node.get_tip() is new_node

    def test_it_should_add_a_leafnode(self, node: nodes.ListItem) -> None:
        new_node = nodes.TextLeafNode(pnode=Mock(), source_text=basetypes.Source.from_text('foo'))
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert node.value is new_node
        assert new_node.parent is node
        assert node.get_tip() is new_node


class TestKeyValue:
    @pytest.fixture
    def node(self, root: nodes.Root, level: int) -> nodes.KeyValue:
        node = nodes.KeyValue(pnode=Mock(), key='foo', level=level)
        root.incorporate_node(node)
        return node

    def test_it_should_add_a_list_at_a_higher_level(self, node: nodes.KeyValue, level: int) -> None:
        new_node = nodes.List(pnode=Mock(), level=level + 4)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert node.value is new_node
        assert new_node.parent is node
        assert node.get_tip() is new_node

    def test_it_should_add_a_list_item_at_a_higher_level_and_create_an_intervening_list(
        self, node: nodes.KeyValue, level: int
    ) -> None:
        new_node = nodes.ListItem(pnode=Mock(), value='foo', level=level + 4)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert isinstance(node.value, nodes.List)
        assert node.value.level == new_node.level

        assert result.parent is node.value
        assert node.value.parent is node
        assert node.get_tip() is new_node

    def test_it_should_cooperatively_add_a_keyvalue_at_the_same_level_to_the_parent_mapping(
        self, node: nodes.KeyValue, level: int
    ) -> None:
        new_node = nodes.KeyValue(pnode=Mock(), key='bar', level=level)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert node.value is None
        assert node.parent is not None
        assert len(node.parent.children) == 2
        assert node.parent.children[-1] is new_node

        assert new_node.parent is node.parent
        assert node.get_tip() is node
        assert node.parent.get_tip() is new_node

    def test_it_should_add_a_keyvalue_at_a_higher_level_and_create_an_intervening_mapping(
        self, node: nodes.KeyValue, level: int
    ) -> None:
        new_node = nodes.KeyValue(pnode=Mock(), key='foo', value='bar', level=level + 4)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert isinstance(node.value, nodes.Mapping)
        assert node.value.level == new_node.level

        assert result.parent is node.value
        assert node.value.parent is node
        assert node.get_tip() is new_node

    def test_it_should_add_a_leafnode(self, node: nodes.KeyValue) -> None:
        new_node = nodes.TextLeafNode(pnode=Mock(), source_text=basetypes.Source.from_text('foo'))
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert node.value is new_node
        assert new_node.parent is node
        assert node.get_tip() is new_node
