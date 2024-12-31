"""Node implementations for parsing SYML documents"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: nocover
    from parsimonious.nodes import Node as PNode

from .basetypes import Pos, Source
from .exceptions import OutOfContextNodeError
from .utils import get_line


@dataclass(kw_only=True)
class SymlNode:
    """A generic node in a SYML document."""

    pnode: PNode = field(repr=False)
    level: int | None = field(default=None)
    parent: SymlNode | None = field(default=None)
    comments: list[Comment] = field(default_factory=list)
    children: list[SymlNode] = field(default_factory=list)

    source: Source = field(init=False)

    def __post_init__(self) -> None:
        self.source = Source.from_node(self.pnode)
        if self.level is not None:
            self.set_level(self.level)

    def set_level(self, level: int) -> None:
        """Set this node's level."""
        self.level = level
        for child in self.children:
            child.set_level(level)

    def as_data(self) -> Any:  # noqa: ANN401  # pragma: nocover
        """Return this node as primitive data types."""
        raise NotImplementedError

    def as_source(self) -> Any:  # noqa: ANN401  # pragma: nocover
        """Return this node as primitive data types with Source objects for strings."""
        raise NotImplementedError

    def get_tip(self) -> SymlNode:
        """Return the tip of this branch."""
        if self.children:
            return self.children[-1].get_tip()
        return self

    def can_add_node(self, node: SymlNode) -> bool:  # noqa: ARG002  # pragma: nocover
        """Check if this node can add a child node."""
        return False

    def add_node(self, node: SymlNode) -> SymlNode:
        """Add a child node."""
        self.children.append(node)
        node.parent = self
        if node.level is None:
            node.set_level(self.level)  # type: ignore[arg-type]
        return node.get_tip()

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


class IndentNode(SymlNode):
    """A node representing an indentation."""


SymlNodes = list[SymlNode]
OptionalSymlNodes = list[SymlNode | None]

NodeOrNodes = SymlNodes | SymlNode | str

OptionalNodes = NodeOrNodes | None


@dataclass(kw_only=True)
class ContainerNode(SymlNode):
    """A container node that may contain a child value."""

    def as_source(self) -> Any:  # noqa: ANN401  # pragma: nocover
        """Return this node as primitive data types with Source objects for strings."""
        if self.children:
            return self.children[0].as_source()
        return None  # pragma: nocover

    def as_data(self) -> Any:  # noqa: ANN401
        """Return the container as primitive data types."""
        if self.children:
            return self.children[0].as_data()
        return None  # pragma: nocover

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
        return not self.children and (node.level is None or (self.level is not None and node.level > self.level))


@dataclass(kw_only=True)
class ParentNode(SymlNode):
    """A parent node that con have multiple children"""

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

    level: int = field(default=0)

    def can_add_node(self, node: SymlNode) -> bool:
        """Check if a child node may be added."""
        return not self.children and (node.level is None or (self.level is not None and node.level >= self.level))


class List(ParentNode):
    """A list node"""

    def can_add_node(self, node: SymlNode) -> bool:
        """Check if a child node can be added."""
        return super().can_add_node(node) and isinstance(node, ListItem)

    def as_source(self) -> Any:  # noqa: ANN401  # pragma: nocover
        """Return this node as primitive data types with Source objects for strings."""
        return [c.as_source() for c in self.children]

    def as_data(self) -> list[Any]:
        """Return this node as primitive data types."""
        return [c.as_data() for c in self.children]


class ListItem(ContainerNode):
    """A list item within a list."""


class Mapping(ParentNode):
    """A mapping of keys to values"""

    def can_add_node(self, node: SymlNode) -> bool:
        """Check if a child node may be added."""
        return super().can_add_node(node) and isinstance(node, KeyValue)

    def as_source(self) -> Any:  # noqa: ANN401  # pragma: nocover
        """Return this node as primitive data types with Source objects for strings."""
        return {c.key.as_source(): c.as_source() for c in self.children}  # type: ignore[attr-defined]

    def as_data(self) -> dict[str, Any]:
        """Return this node as primitive data types."""
        return {c.key.as_data(): c.as_data() for c in self.children}  # type: ignore[attr-defined]


@dataclass(kw_only=True)
class KeyValue(ContainerNode):
    """A key-value item within a mapping"""

    key: KeyLeafNode


@dataclass(kw_only=True)
class TextLeafNode(SymlNode):
    """A leaf node containing a text value."""

    def as_source(self) -> Source:  # pragma: nocover
        """Return this node as primitive data types with Source objects for strings."""
        source = self.source
        for child in self.children:
            source += child.as_source()
        return source

    def as_data(self) -> str:
        """Return this node as primitive types."""
        return '\n'.join([str(self.source)] + [c.as_data() for c in self.children])

    def can_add_node(self, node: SymlNode) -> bool:
        """Check if a child node can be added."""
        return isinstance(node, TextLeafNode)


class KeyLeafNode(SymlNode):
    """A leaf node containing a key value."""

    def can_add_node(self, node: SymlNode) -> bool:  # noqa: ARG002  # pragma: nocover
        """Check if this node can add a child. It can't."""
        return False

    @property
    def key(self) -> Source:
        """Return a Source object representing the key."""
        return Source.from_node(self.pnode)

    def as_source(self) -> Any:  # noqa: ANN401  # pragma: nocover
        """Return this node as primitive data types with Source objects for strings."""
        return self.key

    def as_data(self) -> str:
        """Return the key as a string."""
        return str(self.key)


class Comment(TextLeafNode):
    """A comment node"""

    def as_data(self) -> str:  # pragma: nocover
        """Return an empty string."""
        return ''

    def can_add_node(self, node: SymlNode) -> bool:  # pragma: nocover
        """Check if a child node can be added."""
        return isinstance(node, Comment)
