"""Node implementations for parsing SYML documents"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: nocover
    from parsimonious.nodes import Node as PNode

from .basetypes import Pos, Source, SourceStrBool, StrBool, StrPath
from .exceptions import OutOfContextNodeError
from .utils import get_line


@dataclass(kw_only=True)
class SymlNode:
    """A generic node in a SYML document."""

    pnode: PNode
    level: int | None = field(default=None)
    parent: SymlNode | None = field(default=None)
    comments: list[Comment] = field(default_factory=list)
    children: list[SymlNode] | tuple[SymlNode] = field(default_factory=list)
    value: Any = field(default=None)

    def __post_init__(self) -> None:
        if self.level is not None:
            self.set_level(self.level)

    def set_level(self, level: int) -> None:
        """Set this node's level."""
        self.level = level

    def as_data(self, filename: StrPath = '', raw: bool = False) -> Any:  # noqa: FBT001, FBT002, ANN401  # pragma: nocover
        """Return this node as primitive data types."""
        raise NotImplementedError

    def get_value(self) -> Any:  # noqa: ANN401  # pragma: nocover
        """Return the value of this node."""
        return None

    def get_tip(self) -> SymlNode:
        """Return the tip of this branch."""
        return self

    def can_add_node(self, node: SymlNode) -> bool:  # noqa: ARG002  # pragma: nocover
        """Check if this node can add a child node."""
        return False

    def add_node(self, node: SymlNode) -> SymlNode:  # pragma: nocover
        """Add a child node."""
        raise NotImplementedError

    def incorporate_node(self, node: SymlNode) -> SymlNode:
        """Incorporate the given node into the tree somewhere nearby."""
        if self.can_add_node(node):
            return self.add_node(node)
        if self.parent is not None:
            return self.parent.incorporate_node(node)
        else:  # pragma: nocover  # noqa: RET505
            # Shouldn't ever get here:
            self.fail_to_incorporate_node(node)
            return self  # pragma: nocover

    def fail_to_incorporate_node(self, node: SymlNode) -> None:
        """Report a failure to incorporate a node."""
        pnode = node.pnode
        pos = Pos.from_str_index(pnode.full_text, pnode.start)
        line = get_line(pnode.full_text, pos.line)
        raise OutOfContextNodeError('Failed to incorporate a node', pos, line)


SymlNodes = list[SymlNode]
OptionalSymlNodes = list[SymlNode | None]

NodeOrNodes = SymlNodes | SymlNode | StrBool

OptionalNodes = NodeOrNodes | None


@dataclass(kw_only=True)
class ContainerNode(SymlNode):
    """A container node that may contain a child value."""

    value: SymlNode | StrBool | None = field(default=None)

    def set_level(self, level: int) -> None:
        """Set the level on this node and its child value."""
        self.level = level
        if isinstance(self.value, SymlNode):
            self.value.set_level(level)

    def as_data(self, filename: StrPath = '', raw: bool = False) -> StrBool | None:  # noqa: FBT001, FBT002
        """Return the container as primitive data types."""
        if isinstance(self.value, SymlNode):
            return self.value.as_data(filename, raw=raw)
        else:  # pragma: nocover  # noqa: RET505
            # Shouldn't ever get here.
            return self.value

    def get_value(self) -> Any:  # noqa: ANN401  # pragma: nocover
        """Return the value of this node."""
        return self.value

    def get_tip(self) -> SymlNode:
        """Get the tip of this branch."""
        if self.value is not None and isinstance(self.value, SymlNode):
            return self.value.get_tip()
        return self

    def incorporate_node(self, node: SymlNode) -> SymlNode:
        """Incorporate the given node into this branch."""
        if self.can_add_node(node):
            intermediary: SymlNode | None = None
            if isinstance(node, KeyValue):
                intermediary = Mapping(pnode=node.pnode, level=self.level)
            elif isinstance(node, ListItem):
                intermediary = List(pnode=node.pnode, level=self.level)

            if intermediary is not None:
                intermediary.set_level(node.level)  # type: ignore[arg-type]
                intermediary = self.incorporate_node(intermediary)
                return intermediary.incorporate_node(node)
            return super().incorporate_node(node)
        if self.parent is not None:
            return self.parent.incorporate_node(node)
        else:  # pragma: nocover  # noqa: RET505
            self.fail_to_incorporate_node(node)
            return self

    def can_add_node(self, node: SymlNode) -> bool:
        """Check if this container can add a child node."""
        return self.value is None and (node.level is None or (self.level is not None and node.level > self.level))

    def add_node(self, node: SymlNode) -> SymlNode:
        """Add a child node to this container."""
        self.value = node
        node.parent = self
        if node.level is None:
            node.set_level(self.level)  # type: ignore[arg-type]
        return node.get_tip()


@dataclass(kw_only=True)
class ParentNode(SymlNode):
    """A parent node that con have multiple children"""

    children: list[SymlNode] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.children = list(self.children)

    def set_level(self, level: int) -> None:
        """Set the level of this node and its children."""
        self.level = level
        for child in self.children:
            if isinstance(child, SymlNode):  # pragma: nobranch
                child.set_level(level)

    def get_tip(self) -> SymlNode:
        """Return the tip of this branch."""
        if self.children and isinstance(self.children[-1], SymlNode):
            return self.children[-1].get_tip()
        return self

    def can_add_node(self, node: SymlNode) -> bool:
        """Check if a child node can be added."""
        return node.level is None or (self.level is not None and node.level >= self.level)

    def add_node(self, node: SymlNode) -> SymlNode:
        """Add a child node."""
        self.children.append(node)
        node.parent = self
        if node.level is None:
            node.set_level(self.level)  # type: ignore[arg-type]
        return node.get_tip()


@dataclass(kw_only=True)
class Root(ContainerNode):
    """A root container node for a SYML document"""

    value: SymlNode | None = field(default=None)
    level: int = field(default=0)

    def can_add_node(self, node: SymlNode) -> bool:
        """Check if a child node may be added."""
        return self.value is None and (node.level is None or (self.level is not None and node.level >= self.level))


class Comment(ContainerNode):
    """A comment node"""


class List(ParentNode):
    """A list node"""

    def can_add_node(self, node: SymlNode) -> bool:
        """Check if a child node can be added."""
        return super().can_add_node(node) and isinstance(node, ListItem)

    def as_data(self, filename: StrPath = '', raw: bool = False) -> list[StrBool]:  # noqa: FBT001, FBT002
        """Return this node as primitive data types."""
        return [c.as_data(filename, raw=raw) for c in self.children]


class ListItem(ContainerNode):
    """A list item within a list."""


class Mapping(ParentNode):
    """A mapping of keys to values"""

    def can_add_node(self, node: SymlNode) -> bool:
        """Check if a child node may be added."""
        return super().can_add_node(node) and isinstance(node, KeyValue)

    def as_data(self, filename: StrPath = '', raw: bool = False) -> OrderedDict[StrBool, StrBool]:  # noqa: FBT001, FBT002
        """Return this node as primitive data types."""
        return OrderedDict([(c.key.as_data(filename, raw=raw), c.as_data(filename, raw=raw)) for c in self.children])  # type: ignore[attr-defined]


@dataclass(kw_only=True)
class KeyValue(ContainerNode):
    """A key-value item within a mapping"""

    key: SymlNode | StrBool | None


@dataclass(kw_only=True)
class LeafNode(SymlNode):
    """The tip of a branch"""

    source_text: Source
    value: StrBool | None = field(default=None)

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.value is not None:
            self.value = [(self.pnode, self.value)]  # type: ignore[assignment]
        else:
            self.value = [(self.pnode, self.source_text.value)]  # type: ignore[assignment]

    def get_value(self) -> SourceStrBool:
        """Return this node as a primitive value."""
        return self.value[0][1]  # type: ignore[index]  # pragma: nocover

    def as_data(self, filename: StrPath = '', raw: bool = False) -> SourceStrBool | None:  # noqa: FBT001, FBT002
        """Return this node as primitive types."""
        if raw:
            return self.get_value()
        start_pnode = self.value[0][0]  # type: ignore[index]
        end_pnode = self.value[-1][0]  # type: ignore[index]
        start = Pos.from_str_index(start_pnode.full_text, start_pnode.start)  # type: ignore[union-attr]
        end = Pos.from_str_index(end_pnode.full_text, end_pnode.end)  # type: ignore[union-attr]

        value = self.get_value()

        return Source(
            filename=filename,
            start=start,
            end=end,
            text=str(self.source_text) if isinstance(self.source_text, Source) else self.source_text,
            # Values correspond to lines of text
            value=value.value if isinstance(value, Source) else value,
        )

    def can_add_node(self, node: SymlNode) -> bool:
        """Check if a child node can be added."""
        return isinstance(node, LeafNode) and (
            node.level is None or (self.level is not None and node.level >= self.level)
        )


class TextLeafNode(LeafNode):
    """A leaf node containing a text value."""

    def add_node(self, node: SymlNode) -> SymlNode:
        """Add a node's text value to this node's text."""
        self.source_text += '\n' + str(node.get_value())
        self.value.append((node.pnode, node.get_value()))  # type: ignore[union-attr]
        node.parent = self
        return self.get_tip()

    def get_value(self) -> str:
        """Return this node as a primitive value."""
        return '\n'.join([str(v[1]) for v in self.value])  # type: ignore[union-attr]


class RawValueLeafNode(LeafNode):
    """A leaf node containing a raw value"""

    def get_value(self) -> StrBool:
        """Return this node as a primitive value."""
        return self.value[0][1]  # type: ignore[index]
