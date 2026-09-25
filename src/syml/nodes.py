"""Node implementations for parsing SYML documents"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, NoReturn, cast

if TYPE_CHECKING:  # pragma: nocover
    from parsimonious.nodes import Node as PNode

from .basetypes import Pos, Source, StrPath, get_line_text
from .exceptions import (
    DuplicateKeyError,
    OutOfContextNodeError,
    duplicate_key_description,
    needs_space_after_marker,
    out_of_context_description,
    would_be_key,
)
from .preprocess import PositionMap, is_blank


@dataclass(kw_only=True)
class SymlNode:
    """A generic node in a SYML document."""

    pnode: PNode = field(repr=False)
    level: int | None = field(default=None)
    parent: SymlNode | None = field(default=None)
    children: list[SymlNode] = field(default_factory=list)
    filename: StrPath | None = field(default=None)
    # Threaded from `SymlParser` so every node — leaf or container — can
    # re-anchor its own `source`/error positions onto the caller's
    # original-text coordinates (Contract 08, FR-013, R-02, US8).
    position_map: PositionMap | None = field(default=None, repr=False)
    # Set by `visit_line` on the node a physical line lexes to (Contract 01).
    # `content_pnode` spans the line's content after indentation (used by
    # `TextLeafNode.incorporate_node` to re-read a structure-shaped line as
    # text, R-01); `line_pnode` spans the whole line including indentation
    # (used by `Root` to build a root scalar's first line, R-12). Both stay
    # `None` on inline sub-nodes — only the node a whole physical line lexes
    # to carries them.
    content_pnode: PNode | None = field(default=None, repr=False)
    line_pnode: PNode | None = field(default=None, repr=False)

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
        """Report a failure to incorporate a node. Never reachable outside `Root` (Contract 03 §Placement).

        `_delegate_incorporate_node` only reaches this base-class stub if a
        non-`Root` node ever ended up parentless, which never happens in a
        real parse (every other node type is attached to a parent the moment
        it exists) — `Root` is the sole ancestor with no `parent`, and it
        overrides this method with the real implementation.
        """
        raise NotImplementedError


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

    def incorporate_node(self, node: SymlNode) -> SymlNode:
        """Incorporate the given node into this root (Contract 02 rule 5).

        An empty `Root` offered a plain (non-inline) `TextLeafNode` rebuilds
        it over `line_pnode` — the whole physical line, indentation included
        — rather than the grammar's `text` pnode, which never carries the
        line's leading whitespace. The rebuilt leaf's `baseline` is fixed at
        0 (R-12), so the document is text throughout from here on (rule 1:
        every later level is `>= 0`), and the root scalar keeps its own
        leading indentation as literal characters instead of having it
        stripped like a nested value's anchor column would be.
        """
        if not self.children and isinstance(node, TextLeafNode) and not node.inline and node.line_pnode is not None:
            node = TextLeafNode(
                pnode=node.line_pnode,
                filename=node.filename,
                position_map=node.position_map,
            )
            node.baseline = 0
        return super().incorporate_node(node)

    def fail_to_incorporate_node(self, node: SymlNode) -> NoReturn:
        """Report a failure to incorporate `node`, naming every open column and a hint (Contract 03).

        `_delegate_incorporate_node` only reaches here once it has walked
        all the way up to the root (`Root` is the sole ancestor with no
        `parent`), so `self.position_map` — threaded from the same
        `SymlParser` that built `node` — is the right map to re-anchor this
        position onto the caller's original text.

        Walks `Root`'s rightmost spine (`children[-1]`, repeatedly),
        recording every `List`/`Mapping` node's level and stopping at the
        first `TextLeafNode` reached — the open value's own first line, not
        `get_tip()`'s descent into its last continuation (red team outer
        iteration 6) — or at a childless node otherwise (§Placement).
        """
        pnode = node.pnode
        pos = PositionMap.map(Pos.from_str_index(pnode.full_text, pnode.start), self.position_map)
        line = get_line_text(pnode.full_text, pos.line)
        column = pos.column

        open_blocks, terminal = _walk_open_spine(self)
        kind = 'list item' if isinstance(node, ListItem) else 'key' if isinstance(node, KeyValue) else 'text line'

        continues_at: int | None = None
        if isinstance(terminal, TextLeafNode) and terminal.baseline is not None and column < terminal.baseline:
            continues_at = terminal.baseline

        list_under_key = (
            isinstance(node, ListItem)
            and isinstance(terminal, KeyValue)
            and not terminal.children
            and terminal.level == column
        )
        candidate, missing_space = (
            (None, False) if list_under_key else _hint_candidates(node, pnode, pos, line, open_blocks, terminal)
        )

        description = out_of_context_description(
            line_number=pos.line,
            column=column,
            kind=kind,
            open_columns=list(open_blocks),
            other_kind=open_blocks.get(column),
            continues_at=continues_at,
            list_under_key=list_under_key,
            would_be_key_name=candidate,
            missing_space_after_marker=missing_space,
        )
        raise OutOfContextNodeError(description, pos, line, filename=self.filename)


def _walk_open_spine(root: Root) -> tuple[dict[int, str], SymlNode]:
    """Walk `root`'s rightmost spine, recording every open `List`/`Mapping` level.

    Stops at the first `TextLeafNode` reached (the open value's own first
    line, not `get_tip()`'s descent into its last continuation — red team
    outer iteration 6) or at a childless node otherwise (Contract 03
    §Messages, §Placement).
    """
    open_blocks: dict[int, str] = {}
    cursor: SymlNode = root
    terminal: SymlNode = root
    while True:
        if isinstance(cursor, List):
            open_blocks[cast(int, cursor.level)] = 'list items'
        elif isinstance(cursor, Mapping):
            open_blocks[cast(int, cursor.level)] = 'keys'
        if not cursor.children:
            terminal = cursor
            break
        child = cursor.children[-1]
        if isinstance(child, TextLeafNode):
            terminal = child
            break
        cursor = child
    return open_blocks, terminal


def _hint_candidates(
    node: SymlNode,
    pnode: PNode,
    pos: Pos,
    line: str,
    open_blocks: dict[int, str],
    terminal: SymlNode,
) -> tuple[str | None, bool]:
    """Return hint (a)'s `RUN` and hint (c)'s missing-space flag (Contract 03 §Hints).

    Both hints share the same two candidate lines, checked in the same
    order: the failing line first, then the line above (D26 — hint (c)
    reuses hint (a)'s look-back). Hint (a)'s failing-line gate stays
    `'keys'`-only (a would-be key only makes sense under an open `Mapping`);
    hint (c)'s failing-line gate is any open column (`'keys'` or `'list
    items'`, i.e. form 2) — never form 1 (`column not in open_blocks`),
    where the real problem is indentation and "needs a space" would
    mislead. Only one hint ever wins per candidate line: hint (a)'s pattern
    requires whitespace/EOL after the colon, hint (c)'s requires a
    non-space character there, so the two are mutually exclusive on any
    single line.
    """
    if pos.column in open_blocks:
        if open_blocks[pos.column] == 'keys':
            candidate = would_be_key(line)
            if candidate is not None:
                return candidate, False
        if needs_space_after_marker(line):
            return None, True
    if isinstance(terminal, TextLeafNode) and not terminal.inline and isinstance(node, KeyValue | ListItem):
        above_line = _line_above(pnode.full_text, pos.line)
        if above_line == terminal.source.start.line:
            above_text = get_line_text(pnode.full_text, above_line)
            candidate = would_be_key(above_text)
            if candidate is not None:
                return candidate, False
            if needs_space_after_marker(above_text):
                return None, True
    return None, False


def _line_above(full_text: str, line_number: int) -> int:
    """Return the nearest earlier line that is neither blank nor a column-0 comment (Contract 03 §Messages).

    Blankness uses `preprocess.is_blank` (spaces and tabs only), never
    `str.strip()`, so a NBSP-only continuation counts as a line (FR-009).
    """
    candidate = line_number - 1
    while candidate >= 1:
        text = get_line_text(full_text, candidate)
        if is_blank(text) or text.startswith(('#', '//')):
            candidate -= 1
            continue
        return candidate
    return candidate


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
            key = node.key.as_data()
            message = duplicate_key_description(key)
            raise DuplicateKeyError(
                message,
                node.source.start,
                get_line_text(node.pnode.full_text, node.source.start.line),
                key=key,
                first_position=first.source.start,
                filename=node.filename,
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


@dataclass(kw_only=True)
class TextLeafNode(SymlNode):
    """A leaf node containing a text value."""

    inline: bool = field(default=False)
    # anchor_level/baseline default to these sentinel values until the
    # accepting ContainerNode.add_node sets them on attach (contract 03):
    # anchor_level = self.level, baseline = None if node.inline else node.level.
    anchor_level: int = field(default=-1)
    baseline: int | None = field(default=0)
    # Number of physical blank lines between this continuation and the
    # value's previous line, set by `add_node` on attach (Contract 02 rule
    # 4, FR-004). A column-0 comment line in the gap is neither a line of
    # the value nor a blank line; every physical blank line on either side
    # of it still counts (principal's blank-lines ruling, 2026-09-24).
    blank_lines_before: int = field(default=0)

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
            parts.extend([''] * cast('TextLeafNode', child).blank_lines_before)
            indent = ' ' * max(0, cast(int, child.level) - cast(int, self.baseline))
            parts.append(f'{indent}{child.as_data()}')
        return '\n'.join(parts)

    def accepts_level(self, level: int | None) -> bool:
        """Check whether a candidate at `level` continues this value's text (Contract 02 rule 2).

        `False` for `None` (an inline sub-node, never a whole physical line).
        Before the baseline is fixed (inline value awaiting its first
        continuation), a candidate must be strictly deeper than the value's
        `anchor_level`. Once fixed, a candidate is accepted iff it is at or
        past the baseline (D11 stands).
        """
        if level is None:
            return False
        if self.baseline is None:
            return level > self.anchor_level
        return level >= self.baseline

    def can_add_node(self, node: SymlNode) -> bool:
        """Check if a child node can be added (§5.3, D11, §9.3)."""
        if not isinstance(node, TextLeafNode):
            return False
        return self.accepts_level(node.level)

    def incorporate_node(self, node: SymlNode) -> SymlNode:
        """Incorporate `node`, re-reading a structure-shaped line as this value's text (Contract 02 rule 1).

        Structure is lexed only at a block's first line; once a value is
        text, any later line at or past its baseline is that value's text
        too, whatever shape it lexed to (`- x`, `key: v`, `key:`, an
        indented `#`/`//` comment). A candidate that is not already a
        `TextLeafNode`, carries a `content_pnode` (a whole physical line's
        lex — never an inline sub-node), and sits at or past this leaf's
        threshold gets rebuilt as a `TextLeafNode` over that `content_pnode`
        before falling through to the normal accept/decline walk. A node
        below threshold, already text, or without a `content_pnode` is
        untouched and re-offered up the parent chain unchanged (§9.2) once
        `can_add_node` declines it.
        """
        if not isinstance(node, TextLeafNode) and node.content_pnode is not None and self.accepts_level(node.level):
            node = TextLeafNode(
                pnode=node.content_pnode,
                filename=node.filename,
                position_map=node.position_map,
            )
        return super().incorporate_node(node)

    def add_node(self, node: SymlNode) -> SymlNode:
        """Add a continuation child, fixing and propagating the baseline (D11).

        The baseline is fixed once, on the value's first accepted
        continuation, and propagated unchanged down the rest of the chain so
        every descendant measures its extra indentation against the same
        original baseline rather than its own (uninitialized) default.

        Also counts the physical blank lines between the value's previous
        line (`self`, or its last accepted continuation) and `node`, over
        the NORMALIZED text spanned by `pnode` (Contract 02 rule 4, R-03,
        R-04). A column-0 comment line in the gap is skipped — neither a
        line of the value nor a blank line — but every physical blank line
        on either side of it still counts.
        """
        if self.baseline is None:
            self.baseline = node.level
        child = cast(TextLeafNode, node)
        child.baseline = self.baseline
        prev = self.children[-1] if self.children else self
        full_text = child.pnode.full_text
        gap = full_text[prev.pnode.end : child.pnode.start]
        child.blank_lines_before = sum(1 for line in gap.split('\n')[1:-1] if is_blank(line))
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
