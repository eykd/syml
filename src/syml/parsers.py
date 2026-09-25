"""SYML parsers"""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING, cast

from parsimonious import Grammar, NodeVisitor

from . import nodes
from .basetypes import line_offset_cache_scope
from .exceptions import ParseError
from .preprocess import is_blank, preprocess

if TYPE_CHECKING:  # pragma: nocover
    from parsimonious.nodes import Node

    from .basetypes import StrPath
    from .nodes import OptionalSymlNodes, SymlNode, SymlNodes
    from .preprocess import PositionMap


def _is_zero_length_text(value: SymlNode) -> bool:
    """Return True if `value` is a text leaf with no characters.

    A trailing colon with nothing after it (e.g. ``key: `` at end of line)
    lexes as a `key_value` whose inline text child is empty. Per D6 (§9.3)
    that empty value normalizes away, leaving the `KeyValue` open to accept
    a value from a following nested block instead.
    """
    return isinstance(value, nodes.TextLeafNode) and value.source.text == ''


def _mark_inline(value: SymlNode) -> None:
    """Flag `value` as an inline value (D11) when it is a plain text leaf.

    Marking `TextLeafNode.inline` keeps its continuation baseline open (None)
    until the first accepted continuation line fixes it, instead of fixing
    the baseline at the inline text's own column (see `ContainerNode.add_node`).
    """
    if isinstance(value, nodes.TextLeafNode):
        value.inline = True


def _incorporate_inline_value(parent: SymlNode, value: SymlNode) -> None:
    """Mark `value` inline and incorporate it into `parent`, unless it's empty text (D6, D11)."""
    if not _is_zero_length_text(value):
        _mark_inline(value)
        parent.incorporate_node(value)


class SymlParser(NodeVisitor):  # type: ignore[type-arg]
    """Parser for SYML"""

    grammar = Grammar(
        textwrap.dedent(
            r"""
            document        = (line "\n")* line?
            # Every physical line lexes independently as a comment or as one of
            # the three structure shapes / bare data. Values are literal text
            # (D18): there is no quoted-string rule anywhere, so a `'` or `"` is
            # always ordinary content.
            line            = comment / (indent (structure / data))
            # Tried BEFORE indent: a comment starts at column 0 only (principal
            # ruling 2026-09-24, R-18). One regex, not `("#" / "//") text?`, so
            # no TextLeafNode is ever built for a comment's content.
            comment         = ~"(?:#|//)[^\n]*"
            structure       = list_item / key_value / section
            indent          = ~" *"

            list_item       = value_list_item / guard_list_item
            value_list_item = "-" ws value
            guard_list_item = "-" &eol

            key_value       = key_colon ws data
            section         = key_colon &eol
            key_colon       = key ":"
            # Exactly this pattern (§4.5); ASCII, leading letter.
            key             = ~"[a-z][a-z0-9_-]*"

            eol             = &"\n" / ~r"\Z"
            ws              = ~"[ \t]+"   # Required whitespace (space or tab; §7.5)
            text            = ~"[^\n]*"

            value           = structure / data
            data            = text

            """
        )
    )
    unwrapped_exceptions = (ParseError, RecursionError)

    def __init__(self, filename: StrPath | None = None, position_map: PositionMap | None = None) -> None:
        super().__init__()
        self.filename = filename
        self.position_map = position_map

    def reduce_children(self, children: OptionalSymlNodes) -> SymlNodes:
        """Return all non-null children."""
        return [c for c in children if c is not None]

    def visit_comment(self, node: Node, children: SymlNodes) -> None:  # noqa: ARG002
        """Discard a comment line's content; nothing about it survives into the tree."""
        return

    def visit_line(self, node: Node, children: SymlNodes) -> SymlNode | None:
        """Visit a physical line.

        Returns `None` when the line's chosen alternative is `comment`, and
        when the line's content span (after `indent`) is empty or
        `preprocess.is_blank`. A dropped line leaves no node, so the next
        line's parse node and original-text position are unchanged.
        Otherwise sets `content_pnode` (the `(structure / data)` child's
        parse node) and `line_pnode` (the whole line's parse node) on the
        lexed node and returns it.
        """
        (value,) = children
        chosen = node.children[0]
        if chosen.expr_name == 'comment':
            return None
        content_pnode = chosen.children[1].children[0]
        if is_blank(content_pnode.text):
            return None
        value.content_pnode = content_pnode
        value.line_pnode = node
        return value

    def generic_visit(self, node: Node, children: OptionalSymlNodes) -> SymlNodes | SymlNode | None:  # type: ignore[override]  # noqa: ARG002
        """Visit a generic node."""
        nodes = self.reduce_children(children)
        if not nodes:
            return None
        return nodes[0] if len(nodes) == 1 else nodes

    def visit_text(self, node: Node, children: SymlNodes) -> nodes.TextLeafNode:  # noqa: ARG002
        """Return a text leaf node, in original-text coordinates when normalization ran (Contract 08).

        `level` (fixed in `SymlNode.__post_init__`, before this replaces
        `source`) must stay derived from the NORMALIZED column, so R-11
        indentation logic keeps working on BOM/CRLF documents.
        """
        return nodes.TextLeafNode(pnode=node, filename=self.filename, position_map=self.position_map)

    def visit_key(self, node: Node, children: SymlNodes) -> nodes.KeyLeafNode:  # noqa: ARG002
        """Return a key leaf node, threading `position_map` for original-text coordinates."""
        return nodes.KeyLeafNode(pnode=node, filename=self.filename, position_map=self.position_map)

    def visit_key_colon(self, node: Node, children: SymlNodes) -> nodes.KeyValue:
        """Visit a `key:` colon pair, wrapping the key in a not-yet-populated `KeyValue`."""
        key, _ = children
        return nodes.KeyValue(pnode=node, key=key, filename=self.filename, position_map=self.position_map)  # type: ignore[arg-type]

    def visit_key_value(self, node: Node, children: SymlNodes) -> nodes.KeyValue:  # noqa: ARG002
        """Visit a `key: value` line; its inline value is literal text (D18)."""
        key_value, _, value = children
        _incorporate_inline_value(key_value, value)
        return cast('nodes.KeyValue', key_value)

    def visit_section(self, node: Node, children: SymlNodes) -> nodes.KeyValue:  # noqa: ARG002
        """Visit a standalone `key:` section header."""
        key_value, _ = children
        return cast('nodes.KeyValue', key_value)

    def visit_value_list_item(self, node: Node, children: SymlNodes) -> nodes.ListItem:
        """Visit a list item carrying an inline value."""
        _, _, value = children
        li = nodes.ListItem(pnode=node, filename=self.filename, position_map=self.position_map)
        _incorporate_inline_value(li, value)
        return li

    def visit_guard_list_item(self, node: Node, children: SymlNodes) -> nodes.ListItem:  # noqa: ARG002
        """Visit a bare list item whose value comes from a nested block."""
        return nodes.ListItem(pnode=node, filename=self.filename, position_map=self.position_map)

    def visit_document(self, node: Node, children: OptionalSymlNodes) -> nodes.Root:
        """Visit the document, incorporating every lexed line into a fresh Root's tip.

        `children` nests `Node | list | None` shapes, because `generic_visit`
        collapses a single-item group to its bare item: flatten before
        incorporating.
        """
        root = nodes.Root(pnode=node, filename=self.filename, position_map=self.position_map)
        current: SymlNode = root

        for child in _flatten_lines(children):
            current = current.incorporate_node(child)
        return root


def _flatten_lines(children: OptionalSymlNodes) -> SymlNodes:
    """Flatten `visit_document`'s nested `Node | list | None` children into a flat list of lines."""
    flat: SymlNodes = []
    for child in children:
        if child is None:
            continue
        if isinstance(child, list):
            flat.extend(_flatten_lines(child))
        else:
            flat.append(child)
    return flat


def parse(source_syml: str, filename: StrPath | None = None) -> nodes.Root:
    """Parse a SYML document."""
    with line_offset_cache_scope():
        doc = preprocess(source_syml, filename)
        return SymlParser(filename=filename, position_map=doc.position_map).parse(doc.normalized)
