"""SYML parsers"""

from __future__ import annotations

import textwrap
import unicodedata
from typing import TYPE_CHECKING, cast

from parsimonious import Grammar, NodeVisitor
from parsimonious.nodes import Node

from . import nodes
from .basetypes import line_offset_cache_scope
from .exceptions import ParseError
from .preprocess import preprocess

if TYPE_CHECKING:  # pragma: nocover
    from .basetypes import StrPath
    from .nodes import OptionalNodes, OptionalSymlNodes, SymlNode, SymlNodes
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
            document    = (line "\n")* line?
            line        = indent (structure / data)
            structure   = list_item / key_value / section_line
            indent      = ~" *"
            list_item        = value_list_item / guard_list_item
            value_list_item  = "-" ws value
            guard_list_item  = "-" &eol
            key_value    = section ws data
            section_line = section &eol
            section      = key ":"
            key         = ~"[a-z][a-z0-9_-]*"
            eol         = &"\n" / ~"\Z"
            ws          = ~"[ \t]+"
            text        = ~"[^\n]*"
            value       = structure / data
            data        = text
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

    def visit_blank(self, node: Node, children: SymlNodes) -> None:  # noqa: ARG002
        """Visit a blank."""
        return

    def visit_line(self, node, children):
        """Visit a line."""
        _indent, value = children
        content = node.children[1]
        if content.text.strip(' \t') == '':
            return None
        value.content_pnode = content
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

    def _unused_visit_comment(self, node: Node, children: SymlNodes) -> nodes.Comment:
        """Visit a comment node.

        The trailing `text?` is optional (FR-009): a comment-only line whose
        markers consume the whole line (e.g. '####') leaves it unmatched, so
        parsimonious visits it to `None` rather than a zero-length node.
        Synthesize a zero-width node at the comment's own end position
        instead of dereferencing `.pnode` on `None`.
        """
        _, text = children
        text_pnode = text.pnode if text is not None else Node(node.expr, node.full_text, node.end, node.end)
        return nodes.Comment(pnode=text_pnode, filename=self.filename, position_map=self.position_map)

    def _unused_visit_indent(self, node: Node, children: SymlNodes) -> nodes.IndentNode:  # noqa: ARG002
        """Visit an indentation token."""
        return nodes.IndentNode(
            pnode=node, level=len(node.text.replace('\t', ' ' * 4).strip('\n')), filename=self.filename
        )

    def visit_key_value(self, node, children):
        section, _, value = children
        _incorporate_inline_value(section, value)
        return section

    def visit_section_line(self, node: Node, children: SymlNodes) -> SymlNode:
        """Visit a standalone `key:` section header, applying D19's no-uppercase rule."""
        section, _ = children
        return section

    @staticmethod
    def _is_text_line(section: SymlNode) -> bool:
        """Return whether `section`'s would-be key fails D19, making its line literal text."""
        key_value = cast('nodes.KeyValue', section)  # `section` only ever visits to a KeyValue
        return key_has_uppercase(key_value.key.as_data())

    def _text_leaf(self, node: Node) -> nodes.TextLeafNode:
        """Build a `TextLeafNode` spanning `node`'s whole text (a D19 fallthrough to text)."""
        return nodes.TextLeafNode(pnode=node, filename=self.filename, position_map=self.position_map)

    def visit_section(self, node: Node, children: SymlNodes) -> nodes.KeyValue:
        """Visit a key/value section."""
        key, _ = children
        return nodes.KeyValue(pnode=node, key=key, filename=self.filename, position_map=self.position_map)  # type: ignore[arg-type]

    def visit_value_list_item(self, node: Node, children: SymlNodes) -> nodes.ListItem:
        """Visit a list item carrying an inline value."""
        _, _, value = children
        li = nodes.ListItem(pnode=node, filename=self.filename, position_map=self.position_map)
        _incorporate_inline_value(li, value)
        return li

    def visit_guard_list_item(self, node: Node, children: SymlNodes) -> nodes.ListItem:  # noqa: ARG002
        """Visit a bare list item whose value comes from a nested block."""
        return nodes.ListItem(pnode=node, filename=self.filename, position_map=self.position_map)

    def visit_document(self, node, children):
        root = nodes.Root(pnode=node, filename=self.filename, position_map=self.position_map)
        current = root
        for line in _flatten(children):
            current = current.incorporate_node(line)
        return root


def key_has_uppercase(key: str) -> bool:
    """Return whether `key` contains a code point of General_Category Lu or Lt (D19, §4.5)."""
    return any(unicodedata.category(char) in _UPPERCASE_CATEGORIES for char in key)


_UPPERCASE_CATEGORIES = frozenset({'Lu', 'Lt'})


def parse(source_syml: str, filename: StrPath | None = None) -> nodes.Root:
    """Parse a SYML document."""
    with line_offset_cache_scope():
        doc = preprocess(source_syml, filename)
        return SymlParser(filename=filename, position_map=doc.position_map).parse(doc.normalized)


def _flatten(x):
    if x is None:
        return
    if isinstance(x, list):
        for i in x:
            yield from _flatten(i)
    else:
        yield x
