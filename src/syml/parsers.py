"""SYML parsers"""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

from parsimonious import Grammar, NodeVisitor

from . import nodes
from .exceptions import OutOfContextNodeError
from .preprocess import preprocess

if TYPE_CHECKING:  # pragma: nocover
    from parsimonious.nodes import Node as PNode

    from .basetypes import StrPath
    from .nodes import OptionalNodes, OptionalSymlNodes, SymlNode, SymlNodes


def _is_zero_length_text(value: SymlNode) -> bool:
    """Return True if `value` is a text leaf with no characters.

    A trailing colon with nothing after it (e.g. ``key: `` at end of line)
    lexes as a `key_value` whose inline text child is empty. Per D6 (§9.3)
    that empty value normalizes away, leaving the `KeyValue` open to accept
    a value from a following nested block instead.
    """
    return isinstance(value, nodes.TextLeafNode) and value.source.text == ''


class SymlParser(NodeVisitor):  # type: ignore[type-arg]
    """Parser for SYML"""

    grammar = Grammar(
        textwrap.dedent(
            r"""
            lines       = line*
            line        = indent (comment / blank / structure / value) &eol
            structure   = list_item / key_value / (section &eol)

            indent      = ~"\s*"

            blank       = &eol
            comment     = ~"(#|//+)+" text?

            list_item        = value_list_item / guard_list_item
            value_list_item  = "-" ws value
            guard_list_item  = "-" &eol

            key_value   = section ws data
            section     = key ":"
            key         = ~"[^\s:\x00-\x1f\x7f-\x9f]+"   # Printable, non-whitespace, non-colon (§4.5's \s is the Unicode White_Space set)

            eol         = "\n" / ~"$"
            ws          = ~"[ \t]+"
            text        = ~"[^\n]*"

            value       = structure / data
            data        = text

            """
        )
    )
    unwrapped_exceptions = (OutOfContextNodeError,)

    def __init__(self, filename: StrPath | None = None) -> None:
        super().__init__()
        self.filename = filename

    def reduce_children(self, children: OptionalSymlNodes) -> SymlNodes:
        """Return all non-null children."""
        return [c for c in children if c is not None]

    def visit_blank(self, node: PNode, children: SymlNodes) -> None:  # noqa: ARG002
        """Visit a blank."""
        return

    def visit_line(self, node: PNode, children: SymlNodes) -> OptionalNodes:  # noqa: ARG002
        """Visit a line."""
        _indent, value, _eol = children
        if value is not None:
            # R-11: level comes from the node's own column (set at
            # construction from its own `pnode.start`), not the line's
            # `indent` token — no longer applied here.
            return value
        return None

    def generic_visit(self, node: PNode, children: OptionalSymlNodes) -> SymlNodes | SymlNode | None:  # type: ignore[override]  # noqa: ARG002
        """Visit a generic node."""
        nodes = self.reduce_children(children)
        if not nodes:
            return None
        if len(nodes) == 1:
            return nodes[0]
        else:  # pragma: nocover  # noqa: RET505
            return nodes

    def visit_text(self, node: PNode, children: SymlNodes) -> nodes.TextLeafNode:  # noqa: ARG002
        """Return a text leaf node."""
        return nodes.TextLeafNode(pnode=node, filename=self.filename)

    def visit_key(self, node: PNode, children: SymlNodes) -> nodes.KeyLeafNode:  # noqa: ARG002
        """Return a key leaf node."""
        return nodes.KeyLeafNode(pnode=node, filename=self.filename)

    def visit_comment(self, node: PNode, children: SymlNodes) -> nodes.Comment:  # noqa: ARG002
        """Visit a comment node."""
        _, text = children
        return nodes.Comment(pnode=text.pnode, filename=self.filename)

    def visit_indent(self, node: PNode, children: SymlNodes) -> nodes.IndentNode:  # noqa: ARG002
        """Visit an indentation token."""
        return nodes.IndentNode(
            pnode=node, level=len(node.text.replace('\t', ' ' * 4).strip('\n')), filename=self.filename
        )

    def visit_key_value(self, node: PNode, children: SymlNodes) -> OptionalNodes:  # noqa: ARG002
        """Visit a mapping value."""
        section, _, value = children
        if not _is_zero_length_text(value):
            section.incorporate_node(value)
        return section

    def visit_section(self, node: PNode, children: SymlNodes) -> nodes.KeyValue:
        """Visit a key/value section."""
        key, _ = children
        return nodes.KeyValue(pnode=node, key=key, filename=self.filename)  # type: ignore[arg-type]

    def visit_value_list_item(self, node: PNode, children: SymlNodes) -> nodes.ListItem:
        """Visit a list item carrying an inline value."""
        _, _, value = children
        li = nodes.ListItem(pnode=node, filename=self.filename)
        if value is not None:  # pragma: nobranch
            li.incorporate_node(value)
        return li

    def visit_guard_list_item(self, node: PNode, children: SymlNodes) -> nodes.ListItem:  # noqa: ARG002
        """Visit a bare list item whose value comes from a nested block."""
        return nodes.ListItem(pnode=node, filename=self.filename)

    def visit_lines(self, node: PNode, children: OptionalSymlNodes) -> nodes.Root:
        """Visit the lines within a SYML document."""
        root = nodes.Root(pnode=node, filename=self.filename)
        current: SymlNode = root

        for child in self.reduce_children(children):
            if isinstance(child, nodes.Comment):
                current.comments.append(child)
            else:
                current = current.incorporate_node(child)
        return root


def parse(source_syml: str, filename: StrPath | None = None) -> nodes.Root:
    """Parse a SYML document."""
    doc = preprocess(source_syml, filename)
    return SymlParser(filename=filename).parse(doc.normalized)
