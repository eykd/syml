from unittest.mock import Mock

import pytest

from syml import exceptions, nodes, types


@pytest.fixture
def level() -> int:
    return 4


@pytest.fixture
def root() -> nodes.Root:
    return nodes.Root(Mock())


class TestYamlNode:
    @pytest.fixture
    def node(self) -> nodes.YamlNode:
        return nodes.YamlNode(Mock())

    def test_as_data_is_not_implemented(self, node: nodes.YamlNode) -> None:
        with pytest.raises(NotImplementedError):
            node.as_data('foo.txt')

    def test_add_node_is_not_implemented(self, node: nodes.YamlNode) -> None:
        with pytest.raises(NotImplementedError):
            node.add_node(Mock())

    def test_it_cant_add_a_node(self, node: nodes.YamlNode) -> None:
        assert node.can_add_node(Mock()) is False


class TestRoot:
    def test_it_should_add_a_list(self, root: nodes.RootNode, level: int) -> None:
        new_node = nodes.List(Mock(), level=level)
        result = root.incorporate_node(new_node)
        assert result is new_node
        assert root.value is new_node
        assert new_node.parent is root

    def test_it_should_add_a_list_item_and_create_an_intervening_list(self, root: nodes.RootNode, level: int) -> None:
        new_node = nodes.ListItem(Mock(), 'foo', level=level)
        result = root.incorporate_node(new_node)
        assert result is new_node
        assert isinstance(root.value, nodes.List)

        assert result.parent is root.value
        assert root.value.parent is root

    def test_it_should_add_a_keyvalue_and_create_an_intervening_mapping(self, root: nodes.RootNode, level: int) -> None:
        new_node = nodes.KeyValue(Mock(), 'foo', value='bar', level=level)
        result = root.incorporate_node(new_node)
        assert result is new_node
        assert isinstance(root.value, nodes.Mapping)

        assert result.parent is root.value
        assert root.value.parent is root


class TestList:
    @pytest.fixture
    def node(self, root: nodes.RootNode, level: int) -> nodes.List:
        node = root.add_node(nodes.List(Mock()))
        node.level = level
        return node

    def test_it_should_add_a_list_item_at_a_higher_level(self, node: nodes.YamlNode, level: int) -> None:
        new_node = nodes.ListItem(Mock(), value='foo', level=level + 4)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert result.parent is node
        assert new_node in node.children

    def test_it_should_not_add_a_list_item_at_a_lower_level(self, node: nodes.YamlNode, level: int) -> None:
        pnode = Mock(
            full_text='    - bar\n   - foo',
            text='- foo',
            start=16,
        )
        new_node = nodes.ListItem(pnode, value='foo', level=level - 1)
        with pytest.raises(exceptions.OutOfContextNodeError):
            node.incorporate_node(new_node)

    def test_it_should_not_add_a_keyvalue_item_at_a_higher_level(self, node: nodes.YamlNode, level: int) -> None:
        pnode = Mock(
            full_text='    - bar\n     foo: baz',
            text='foo: baz',
            start=level + 4,
        )
        new_node = nodes.KeyValue(pnode, key='foo', value='bar', level=level + 4)
        with pytest.raises(exceptions.OutOfContextNodeError):
            node.incorporate_node(new_node)


class TestMapping:
    @pytest.fixture
    def node(self, root: nodes.RootNode, level: int) -> nodes.Mapping:
        node = root.add_node(nodes.Mapping(Mock()))
        node.level = level
        return node

    def test_it_should_add_a_keyvalue_at_a_higher_level(self, node: nodes.YamlNode, level: int) -> None:
        new_node = nodes.KeyValue(Mock(), 'foo', value='bar', level=level + 4)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert result.parent is node
        assert new_node in node.children

    def test_it_should_not_add_a_keyvalue_at_a_lower_level(self, node: nodes.YamlNode, level: int) -> None:
        pnode = Mock(
            full_text='    foo: bar\n   bar: baz',
            text='bar: baz',
            start=14,
        )
        new_node = nodes.KeyValue(pnode, 'foo', value='bar', level=level - 1)
        with pytest.raises(exceptions.OutOfContextNodeError):
            node.incorporate_node(new_node)

    def test_it_should_not_add_a_listitem_at_a_higher_level(self, node: nodes.YamlNode, level: int) -> None:
        pnode = Mock(
            full_text='    foo: bar\n       - baz',
            text='- baz',
            start=level + 4,
        )
        new_node = nodes.ListItem(pnode, value='foo', level=level + 4)
        with pytest.raises(exceptions.OutOfContextNodeError):
            node.incorporate_node(new_node)


class TestListItem:
    @pytest.fixture
    def node(self, root: nodes.RootNode, level: int) -> nodes.ListItem:
        return root.incorporate_node(nodes.ListItem(Mock(), level=level))

    def test_it_should_add_a_list_at_a_higher_level(self, node: nodes.YamlNode, level: int) -> None:
        new_node = nodes.List(Mock(), level=level + 4)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert node.value is new_node
        assert new_node.parent is node

    def test_it_should_add_a_list_item_at_a_higher_level_and_create_an_intervening_list(
        self, node: nodes.YamlNode, level: int
    ) -> None:
        new_node = nodes.ListItem(Mock(), 'foo', level=level + 4)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert isinstance(node.value, nodes.List)
        assert node.value.level == new_node.level

        assert result.parent is node.value
        assert node.value.parent is node

    def test_it_should_cooperatively_add_a_list_item_at_the_same_level_to_the_parent_list(
        self, node: nodes.YamlNode, level: int
    ) -> None:
        new_node = nodes.ListItem(Mock(), 'foo', level=level)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert node.value is None
        assert len(node.parent.children) == 2
        assert node.parent.children[-1] is new_node

        assert new_node.parent is node.parent

    def test_it_should_add_a_keyvalue_at_a_higher_level_and_create_an_intervening_mapping(
        self, node: nodes.YamlNode, level: int
    ) -> None:
        new_node = nodes.KeyValue(Mock(), 'foo', value='bar', level=level + 4)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert isinstance(node.value, nodes.Mapping)
        assert node.value.level == new_node.level

        assert result.parent is node.value
        assert node.value.parent is node

    def test_it_should_add_a_keyvalue_with_no_level_and_create_an_intervening_mapping(
        self, node: nodes.YamlNode
    ) -> None:
        new_node = nodes.KeyValue(Mock(), 'foo', value='bar', level=None)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert isinstance(node.value, nodes.Mapping)
        assert node.value.level == new_node.level

        assert result.parent is node.value
        assert node.value.parent is node

    def test_it_should_add_a_leafnode(self, node: nodes.YamlNode) -> None:
        new_node = nodes.LeafNode(Mock(), types.Source.from_text('foo'))
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert node.value is new_node
        assert new_node.parent is node


class TestKeyValue:
    @pytest.fixture
    def node(self, root: nodes.RootNode, level: int) -> nodes.KeyValue:
        return root.incorporate_node(nodes.KeyValue(Mock(), 'foo', level=level))

    def test_it_should_add_a_list_at_a_higher_level(self, node: nodes.YamlNode, level: int) -> None:
        new_node = nodes.List(Mock(), level=level + 4)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert node.value is new_node
        assert new_node.parent is node

    def test_it_should_add_a_list_item_at_a_higher_level_and_create_an_intervening_list(
        self, node: nodes.YamlNode, level: int
    ) -> None:
        new_node = nodes.ListItem(Mock(), 'foo', level=level + 4)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert isinstance(node.value, nodes.List)
        assert node.value.level == new_node.level

        assert result.parent is node.value
        assert node.value.parent is node

    def test_it_should_cooperatively_add_a_keyvalue_at_the_same_level_to_the_parent_mapping(
        self, node: nodes.YamlNode, level: int
    ) -> None:
        new_node = nodes.KeyValue(Mock(), 'bar', level=level)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert node.value is None
        assert len(node.parent.children) == 2
        assert node.parent.children[-1] is new_node

        assert new_node.parent is node.parent

    def test_it_should_add_a_keyvalue_at_a_higher_level_and_create_an_intervening_mapping(
        self, node: nodes.YamlNode, level: int
    ) -> None:
        new_node = nodes.KeyValue(Mock(), 'foo', value='bar', level=level + 4)
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert isinstance(node.value, nodes.Mapping)
        assert node.value.level == new_node.level

        assert result.parent is node.value
        assert node.value.parent is node

    def test_it_should_add_a_leafnode(self, node: nodes.YamlNode) -> None:
        new_node = nodes.LeafNode(Mock(), types.Source.from_text('foo'))
        result = node.incorporate_node(new_node)
        assert result is new_node
        assert node.value is new_node
        assert new_node.parent is node
