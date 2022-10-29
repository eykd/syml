from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable
from typing import Any
from typing import List as TList
from typing import Optional, Union

from parsimonious.nodes import Node as PNode

from .exceptions import OutOfContextNodeError
from .types import Pos, Source, SourceStrBool, StrBool, StrPath
from .utils import get_line


class YamlNode:
    def __init__(
        self, pnode: PNode, level: Optional[int] = None, parent: Optional[YamlNode] = None, comments: Iterable = ()
    ):
        self.pnode = pnode
        self._level = None
        self.parent = parent
        self.comments = list(comments)
        self.level = level

    @property
    def level(self) -> Optional[int]:
        return self._level

    @level.setter
    def level(self, level: int) -> None:
        self._set_level(level)

    def _set_level(self, level: int) -> None:
        self._level = level

    def as_data(self, filename: StrPath = "", raw: bool = False) -> Any:
        raise NotImplementedError()

    def get_value(self):
        return None

    def get_tip(self) -> YamlNode:
        return self

    def can_add_node(self, node: YamlNode) -> bool:
        return False

    def add_node(self, node: YamlNode) -> YamlNode:
        raise NotImplementedError()

    def incorporate_node(self, node: YamlNode) -> YamlNode:
        if self.can_add_node(node):
            return self.add_node(node)
        else:
            if self.parent is not None:
                return self.parent.incorporate_node(node)
            else:  # pragma: no cover
                # Shouldn't ever get here:
                self.fail_to_incorporate_node(node)
                return self

    def fail_to_incorporate_node(self, node: YamlNode) -> None:
        pnode = node.pnode
        pos = Pos.from_str_index(pnode.full_text, pnode.start)
        line = get_line(pnode.full_text, pos.line)
        raise OutOfContextNodeError("Line %s, column %s:\n%s" % (pos.line, pos.column, line))


YamlNodes = Iterable[Optional[YamlNode]]

NodeOrNodes = Union[YamlNodes, YamlNode, StrBool]

OptionalNodes = Optional[NodeOrNodes]


class ContainerNode(YamlNode):
    def __init__(self, pnode: PNode, value: Optional[Union[YamlNode, StrBool]] = None, **kwargs) -> None:
        self.value = value
        super().__init__(pnode, **kwargs)

    def _set_level(self, level: int) -> None:
        self._level = level
        if isinstance(self.value, YamlNode):
            self.value.level = level

    def as_data(self, filename: StrPath = "", raw: bool = False) -> Optional[StrBool]:
        if isinstance(self.value, YamlNode):
            return self.value.as_data(filename, raw=raw)
        else:  # pragma: no cover
            # Shouldn't ever get here.
            return self.value

    def get_value(self):
        return self.value

    def get_tip(self) -> YamlNode:
        if self.value is not None and isinstance(self.value, YamlNode):
            return self.value.get_tip()
        else:
            return self

    def incorporate_node(self, node: YamlNode) -> YamlNode:
        if self.can_add_node(node):
            intermediary: Optional[YamlNode] = None
            if isinstance(node, KeyValue):
                intermediary = Mapping(node.pnode)
            elif isinstance(node, ListItem):
                intermediary = List(node.pnode)

            if intermediary is not None:
                intermediary.level = node.level
                intermediary = self.incorporate_node(intermediary)
                return intermediary.incorporate_node(node)
            else:
                return super().incorporate_node(node)
        else:
            if self.parent is not None:
                return self.parent.incorporate_node(node)
            else:
                self.fail_to_incorporate_node(node)
                return self

    def can_add_node(self, node: YamlNode):
        return self.value is None and (node.level is None or (self.level is not None and node.level > self.level))

    def add_node(self, node: YamlNode):
        self.value = node
        node.parent = self
        if node.level is None:
            node.level = self.level
        return node.get_tip()


class ParentNode(YamlNode):
    def __init__(self, pnode: PNode, children: Iterable = (), **kwargs) -> None:
        self.children = list(children)
        super().__init__(pnode, **kwargs)

    def _set_level(self, level: int) -> None:
        self._level = level
        for child in self.children:
            if isinstance(child, YamlNode):
                child.level = level

    def get_tip(self) -> YamlNode:
        if self.children and isinstance(self.children[-1], YamlNode):
            return self.children[-1].get_tip()
        else:
            return self

    def can_add_node(self, node: YamlNode) -> bool:
        return node.level is None or (self.level is not None and node.level >= self.level)

    def add_node(self, node: YamlNode):
        self.children.append(node)
        node.parent = self
        if node.level is None:
            node.level = self.level
        return node.get_tip()


class Root(ContainerNode):
    def __init__(self, pnode: PNode) -> None:
        super().__init__(pnode, level=0)

    def can_add_node(self, node: YamlNode) -> bool:
        return self.value is None and (node.level is None or (self.level is not None and node.level >= self.level))


class Comment(ContainerNode):
    pass


class List(ParentNode):
    def can_add_node(self, node: YamlNode) -> bool:
        return super().can_add_node(node) and isinstance(node, ListItem)

    def as_data(self, filename: StrPath = "", raw: bool = False) -> TList[StrBool]:
        return [c.as_data(filename, raw=raw) for c in self.children]


class ListItem(ContainerNode):
    pass


class Mapping(ParentNode):
    def can_add_node(self, node: YamlNode) -> bool:
        return super().can_add_node(node) and isinstance(node, KeyValue)

    def as_data(self, filename: StrPath = "", raw: bool = False) -> OrderedDict[StrBool, StrBool]:
        return OrderedDict([(c.key.as_data(filename, raw=raw), c.as_data(filename, raw=raw)) for c in self.children])


class KeyValue(ContainerNode):
    def __init__(self, pnode: PNode, key: StrBool, **kwargs):
        self.key = key
        super().__init__(pnode, **kwargs)


class LeafNode(YamlNode):
    def __init__(self, pnode: PNode, source_text: Source, value: Optional[StrBool] = None, **kwargs):
        self.source_text = source_text
        self.value = [(pnode, value)] if value is not None else [(pnode, source_text.value)]
        super().__init__(pnode, **kwargs)

    def get_value(self) -> SourceStrBool:
        return self.value[0][1]

    def as_data(self, filename: StrPath = "", raw: bool = False) -> Optional[SourceStrBool]:
        if raw:
            return self.get_value()
        else:
            start_pnode = self.value[0][0]
            end_pnode = self.value[-1][0]
            start = Pos.from_str_index(start_pnode.full_text, start_pnode.start)
            end = Pos.from_str_index(end_pnode.full_text, end_pnode.end)

            value = self.get_value()

            return Source(
                filename=filename,
                start=start,
                end=end,
                text=str(self.source_text) if isinstance(self.source_text, Source) else self.source_text,
                # Values correspond to lines of text
                value=value.value if isinstance(value, Source) else value,
            )

    def can_add_node(self, node: YamlNode) -> bool:
        return isinstance(node, LeafNode) and (
            node.level is None or (self.level is not None and node.level >= self.level)
        )


class TextLeafNode(LeafNode):
    def add_node(self, node: YamlNode) -> YamlNode:
        self.source_text += "\n" + str(node.get_value())
        self.value.append((node.pnode, node.get_value()))
        node.parent = self
        return self.get_tip()

    def get_value(self) -> str:
        return "\n".join([str(v[1]) for v in self.value])


class RawValueLeafNode(LeafNode):
    def get_value(self) -> StrBool:
        return self.value[0][1]
