"""Node implementations for parsing SYML documents"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, NoReturn, cast

if TYPE_CHECKING:  # pragma: nocover
    from parsimonious.nodes import Node as PNode

from .basetypes import Pos, Source, StrPath, get_line_text
from .exceptions import DuplicateKeyError, OutOfContextNodeError, error_message
from .preprocess import PositionMap


@dataclass(kw_only=True)
class SymlNode:
    """A generic node in a SYML document."""

    pnode: PNode = field(repr=False)
    level: int | None = field(default=None)
    parent: SymlNode | None = field(default=None)
    comments: list[Comment] = field(default_factory=list)
    children: list[SymlNode] = field(default_factory=list)
    filename: StrPath | None = field(default=None)
    # Threaded from `SymlParser` so every node — leaf or container — can
    # re-anchor its own `source`/error positions onto the caller's
    # original-text coordinates (Contract 08, FR-013, R-02, US8).
    position_map: PositionMap | None = field(default=None, repr=False)

    source: Source = field(init=False)

    def __post_init__(self) -> None:
        self.source = Source.from_node(self.pnode, filename=self.filename)
        if self.level is None:
            # R-11: a node's level is the 0-indexed column where its own
            # marker or content begins — its own `pnode.start`, not
            # anything inherited from the line it's on. Derived from the
            # NORMALIZED source, before any original-text re-anchoring below.
            self.level = self.source.start.column
        if self.position_map is not None:
            self.source = self.position_map.to_original_source(self.source)

    def as_data(self) -> Any:  # noqa: ANN401
        """Return this node as primitive data types."""
        raise NotImplementedError

    def as_source(self) -> Any:  # noqa: ANN401
        """Return this node as primitive data types with Source objects for strings."""
        raise NotImplementedError

    def get_tip(self) -> SymlNode:
        """Return the tip of this branch."""
        if self.children:
            return self.children[-1].get_tip()
        return self

    def can_add_node(self, node: SymlNode) -> bool:  # noqa: ARG002
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
        return self._delegate_incorporate_node(node)

    def _delegate_incorporate_node(self, node: SymlNode) -> SymlNode:
        """Hand the node to the parent, or fail if there is none."""
        if self.parent is not None:
            return self.parent.incorporate_node(node)
        return self.fail_to_incorporate_node(node)

    def fail_to_incorporate_node(self, node: SymlNode) -> NoReturn:
        """Report a failure to incorporate a node, in original-text coordinates (Contract 05, 08).

        `_delegate_incorporate_node` only reaches here once it has walked all
        the way up to the root (the sole ancestor with no `parent`), so
        `self.position_map` — threaded from the same `SymlParser` that built
        `node` — is the right map to re-anchor this position onto the
        caller's original text.
        """
        pnode = node.pnode
        pos = PositionMap.map(Pos.from_str_index(pnode.full_text, pnode.start), self.position_map)
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
        return self._delegate_incorporate_node(node)

    @staticmethod
    def _intermediary_for(node: SymlNode) -> ParentNode | None:
        """Return the auto-inserted Mapping/List container a bare node needs, if any (§9.4)."""
        if isinstance(node, KeyValue):
            return Mapping(pnode=node.pnode, level=node.level, filename=node.filename, position_map=node.position_map)
        if isinstance(node, ListItem):
            return List(pnode=node.pnode, level=node.level, filename=node.filename, position_map=node.position_map)
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

    def incorporate_node(self, node):
        if not self.children and type(node) is TextLeafNode and getattr(node, 'line_pnode', None) is not None:
            node = TextLeafNode(pnode=node.line_pnode, filename=node.filename, position_map=node.position_map)
        return super().incorporate_node(node)


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

    pass


@dataclass(kw_only=True)
class TextLeafNode(SymlNode):
    """A leaf node containing a text value."""

    inline: bool = field(default=False)
    blank_lines_before: int = field(default=0)
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

    def accepts_level(self, level):
        if level is None:
            return False
        if self.baseline is None:
            return level > self.anchor_level
        return level >= self.baseline

    def incorporate_node(self, node):
        if not isinstance(node, TextLeafNode) and self.accepts_level(node.level) and getattr(node, 'content_pnode', None) is not None:
            node = TextLeafNode(pnode=node.content_pnode, filename=node.filename, position_map=node.position_map)
        return super().incorporate_node(node)

    def as_data(self) -> str:
        """Return this node as primitive types, preserving indentation past the baseline (D11).

        Every accepted child is a `TextLeafNode` with a level fixed by the
        grammar and a baseline fixed by `add_node` on first acceptance
        (never `None` once a child exists), so both are cast rather than
        branched on.
        """
        parts = [str(self.source)]
        for child in self.children:
            parts.extend([''] * child.blank_lines_before)
            indent = ' ' * max(0, cast(int, child.level) - cast(int, self.baseline))
            parts.append(f'{indent}{child.as_data()}')
        return '\n'.join(parts)

    def can_add_node(self, node: SymlNode) -> bool:
        """Check if a child node can be added (§5.3, D11, §9.3)."""
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
        prev = self.children[-1] if self.children else self
        node.blank_lines_before = node.pnode.full_text[prev.pnode.end:node.pnode.start].count('\n') - 1
        cast(TextLeafNode, node).baseline = self.baseline
        super().add_node(node)
        return self


class KeyLeafNode(SymlNode):
    """A leaf node containing a key value."""

    @property
    def key(self) -> Source:
        """Return a Source object representing the key, in original-text coordinates.

        `self.source` is already re-anchored onto original-text coordinates
        by the base class's `__post_init__` when `position_map` is set
        (Contract 08, FR-013, R-02, US8).
        """
        return self.source

    def as_source(self) -> Any:  # noqa: ANN401
        """Return this node as primitive data types with Source objects for strings."""
        return self.key

    def as_data(self) -> str:
        """Return the key as a string."""
        return str(self.key)


class Comment(TextLeafNode):
    """A comment node"""
