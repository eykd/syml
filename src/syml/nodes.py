"""Node implementations for parsing SYML documents"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:  # pragma: nocover
    from parsimonious.nodes import Node as PNode

from .basetypes import Pos, Source, StrPath
from .exceptions import DuplicateKeyError, OutOfContextNodeError, error_message
from .utils import get_line_text


@dataclass(kw_only=True)
class SymlNode:
    """A generic node in a SYML document."""

    pnode: PNode = field(repr=False)
    level: int | None = field(default=None)
    parent: SymlNode | None = field(default=None)
    comments: list[Comment] = field(default_factory=list)
    children: list[SymlNode] = field(default_factory=list)
    filename: StrPath | None = field(default=None)

    source: Source = field(init=False)

    def __post_init__(self) -> None:
        self.source = Source.from_node(self.pnode, filename=self.filename)
        if self.level is None:
            # R-11: a node's level is the 0-indexed column where its own
            # marker or content begins — its own `pnode.start`, not
            # anything inherited from the line it's on.
            self.level = self.source.start.column

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
        line = get_line_text(pnode.full_text, pos.line)
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

    def as_source(self) -> Any:  # noqa: ANN401
        """Return this node as primitive data types with Source objects for strings.

        A childless container — including a `Root` for an empty or
        comment-only document — yields a zero-width `Source` at its own
        `source.end` rather than `None`, at every depth (Contract 03
        §Absent values, FR-005).
        """
        if self.children:
            return self.children[0].as_source()
        return Source(filename=self.source.filename, start=self.source.end, end=self.source.end, text='')

    def as_data(self) -> Any:  # noqa: ANN401
        """Return the container as primitive data types.

        A childless container — including a `Root` for an empty or
        comment-only document — yields `''` rather than `None`, at every
        depth (Contract 03 §Absent values, FR-005).
        """
        if self.children:
            return self.children[0].as_data()
        return ''

    def incorporate_node(self, node: SymlNode) -> SymlNode:
        """Incorporate the given node into this branch."""
        if self.can_add_node(node):
            intermediary = self._intermediary_for(node)
            if intermediary is not None:
                incorporated = self.incorporate_node(intermediary)
                return incorporated.incorporate_node(node)
            return super().incorporate_node(node)
        if self.parent is not None:
            return self.parent.incorporate_node(node)
        else:  # pragma: nocover  # noqa: RET505
            self.fail_to_incorporate_node(node)
            return self

    @staticmethod
    def _intermediary_for(node: SymlNode) -> ParentNode | None:
        """Return the auto-inserted Mapping/List container a bare node needs, if any (§9.4)."""
        if isinstance(node, KeyValue):
            return Mapping(pnode=node.pnode, level=node.level, filename=node.filename)
        if isinstance(node, ListItem):
            return List(pnode=node.pnode, level=node.level, filename=node.filename)
        return None

    def can_add_node(self, node: SymlNode) -> bool:
        """Check if this container can add a child node."""
        return not self.children and (node.level is None or (self.level is not None and node.level > self.level))

    def add_node(self, node: SymlNode) -> SymlNode:
        """Add a child node, fixing anchor_level/baseline on an attached leaf (contract 03)."""
        if isinstance(node, TextLeafNode) and self.level is not None:
            node.anchor_level = self.level
            node.baseline = None if node.inline else node.level
        return super().add_node(node)


@dataclass(kw_only=True)
class ParentNode(SymlNode):
    """A parent node that can have multiple children"""

    def can_add_node(self, node: SymlNode) -> bool:
        """Check if a child node can be added.

        Siblings must sit at exactly this node's level (§9.3) — a
        candidate that is deeper falls through so the caller walks back
        up the parent chain per §9.2 instead of being absorbed here.
        """
        return node.level is None or (self.level is not None and node.level == self.level)


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

    def as_source(self) -> Any:  # noqa: ANN401
        """Return this node as primitive data types with Source objects for strings."""
        return [c.as_source() for c in self.children]

    def as_data(self) -> list[Any]:
        """Return this node as primitive data types."""
        return [c.as_data() for c in self.children]


class ListItem(ContainerNode):
    """A list item within a list."""


@dataclass(kw_only=True)
class Mapping(ParentNode):
    """A mapping of keys to values"""

    keys: dict[str, KeyValue] = field(default_factory=dict)

    def can_add_node(self, node: SymlNode) -> bool:
        """Check if a child node may be added.

        Raises `DuplicateKeyError` immediately when a same-level
        `KeyValue` repeats an already-incorporated sibling's key
        (FR-007, §8.3, §10.3), rather than falling through to §9.2's
        walk-up.
        """
        if not (super().can_add_node(node) and isinstance(node, KeyValue)):
            return False
        first = self.keys.get(node.key.as_data())
        if first is not None:
            raise DuplicateKeyError(
                error_message('Duplicate key', node.filename),
                node.source.start,
                get_line_text(node.pnode.full_text, node.source.start.line),
                key=node.key.as_data(),
                first_position=first.source.start,
            )
        return True

    def add_node(self, node: SymlNode) -> SymlNode:
        """Add a child node, recording its key for duplicate detection."""
        kv = cast('KeyValue', node)  # can_add_node admitted only a KeyValue
        result = super().add_node(kv)
        self.keys[kv.key.as_data()] = kv
        return result

    def as_source(self) -> Any:  # noqa: ANN401
        """Return this node as primitive data types with Source objects for strings."""
        return {c.key.as_source(): c.as_source() for c in self.children}  # type: ignore[attr-defined]

    def as_data(self) -> dict[str, Any]:
        """Return this node as primitive data types."""
        return {c.key.as_data(): c.as_data() for c in self.children}  # type: ignore[attr-defined]


@dataclass(kw_only=True)
class KeyValue(ContainerNode):
    """A key-value item within a mapping"""

    key: KeyLeafNode

    def can_add_node(self, node: SymlNode) -> bool:
        """Check if this key-value item can add a child node.

        A block value must be strictly deeper than its own key's column
        (R-11) — except a nested list (the YAML-style "indentless
        sequence"), whose items conventionally align with the key that
        introduces them rather than sitting a column deeper.
        """
        if isinstance(node, ListItem | List):
            return not self.children and (node.level is None or (self.level is not None and node.level >= self.level))
        return super().can_add_node(node)


@dataclass(kw_only=True)
class TextLeafNode(SymlNode):
    """A leaf node containing a text value."""

    inline: bool = field(default=False)
    quoted: bool = field(default=False)
    # anchor_level/baseline default to these sentinel values until the
    # accepting ContainerNode.add_node sets them on attach (contract 03):
    # anchor_level = self.level, baseline = None if node.inline else node.level.
    anchor_level: int = field(default=-1)
    baseline: int | None = field(default=0)

    def as_source(self) -> Source:
        """Return this node's Source, spanning through the last continuation line (Contract 08).

        `start` stays at this node's own first character; `end` moves to the
        last accepted continuation's end; `text` mirrors `as_data()`,
        including indentation preserved past the baseline (D11), so
        `str(node.as_source()) == node.as_data()` holds.
        """
        tip = self.get_tip()
        return Source(filename=self.source.filename, start=self.source.start, end=tip.source.end, text=self.as_data())

    def as_data(self) -> str:
        """Return this node as primitive types, preserving indentation past the baseline (D11).

        Every accepted child is a `TextLeafNode` with a level fixed by the
        grammar and a baseline fixed by `add_node` on first acceptance
        (never `None` once a child exists), so both are cast rather than
        branched on.
        """
        parts = [str(self.source)]
        for child in self.children:
            indent = ' ' * max(0, cast(int, child.level) - cast(int, self.baseline))
            first, sep, rest = child.as_data().partition('\n')
            parts.append(f'{indent}{first}{sep}{rest}')
        return '\n'.join(parts)

    def can_add_node(self, node: SymlNode) -> bool:
        """Check if a child node can be added (§5.3, D11, §9.3)."""
        if self.quoted:
            return False
        if not isinstance(node, TextLeafNode) or node.level is None:
            return False
        if self.baseline is None:
            return node.level > self.anchor_level
        return node.level >= self.baseline

    def add_node(self, node: SymlNode) -> SymlNode:
        """Add a continuation child, fixing and propagating the baseline (D11).

        The baseline is fixed once, on the value's first accepted
        continuation, and propagated unchanged down the rest of the chain so
        every descendant measures its extra indentation against the same
        original baseline rather than its own (uninitialized) default.
        """
        if self.baseline is None:
            self.baseline = node.level
        cast(TextLeafNode, node).baseline = self.baseline
        super().add_node(node)
        return self


class KeyLeafNode(SymlNode):
    """A leaf node containing a key value."""

    def can_add_node(self, node: SymlNode) -> bool:  # noqa: ARG002  # pragma: nocover
        """Check if this node can add a child. It can't."""
        return False

    @property
    def key(self) -> Source:
        """Return a Source object representing the key."""
        return Source.from_node(self.pnode, filename=self.filename)

    def as_source(self) -> Any:  # noqa: ANN401
        """Return this node as primitive data types with Source objects for strings."""
        return self.key

    def as_data(self) -> str:
        """Return the key as a string."""
        return str(self.key)


class Comment(TextLeafNode):
    """A comment node"""
