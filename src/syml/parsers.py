"""SYML parsers"""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

from parsimonious import Grammar, NodeVisitor

from . import nodes
from .exceptions import OutOfContextNodeError

if TYPE_CHECKING:  # pragma: nocover
    from parsimonious.nodes import Node as PNode

    from .nodes import OptionalNodes, OptionalSymlNodes, SymlNode, SymlNodes


class SymlParser(NodeVisitor):  # type: ignore[type-arg]
    """Parser for SYML"""

    grammar = Grammar(
        textwrap.dedent(
            r"""
            lines       = line*
            line        = indent (comment / blank / structure / value) &eol
            structure   = list_item / key_value / section

            indent      = ~"\s*"

            blank       = &eol
            comment     = ~"(#|//+)+" text?

            list_item   = "-" ws value

            key_value   = section ws data
            section     = key ":"
            key         = ~"[^\s:]+"

            eol         = "\n" / ~"$"
            ws          = ~"[ \t]+"
            text        = ~".+"

            value       = structure / data
            data        = text

            """
        )
    )
    unwrapped_exceptions = (OutOfContextNodeError,)

    def reduce_children(self, children: OptionalSymlNodes) -> SymlNodes:
        """Return all non-null children."""
        return [c for c in children if c is not None]

    def visit_blank(self, node: PNode, children: SymlNodes) -> None:  # noqa: ARG002
        """Visit a blank."""
        return

    def visit_line(self, node: PNode, children: SymlNodes) -> OptionalNodes:  # noqa: ARG002
        """Visit a line."""
        indent, value, _ = children
        if value is not None:
            value.set_level(indent.level)  # type: ignore[arg-type]
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
        return nodes.TextLeafNode(pnode=node)

    def visit_key(self, node: PNode, children: SymlNodes) -> nodes.KeyLeafNode:  # noqa: ARG002
        """Return a key leaf node."""
        return nodes.KeyLeafNode(pnode=node)

    def visit_comment(self, node: PNode, children: SymlNodes) -> nodes.Comment:  # noqa: ARG002
        """Visit a comment node."""
        _, text = children
        return nodes.Comment(pnode=text.pnode)

    def visit_indent(self, node: PNode, children: SymlNodes) -> nodes.IndentNode:  # noqa: ARG002
        """Visit an indentation token."""
        return nodes.IndentNode(pnode=node, level=len(node.text.replace('\t', ' ' * 4).strip('\n')))

    def visit_key_value(self, node: PNode, children: SymlNodes) -> OptionalNodes:  # noqa: ARG002
        """Visit a mapping value."""
        section, _, value = children
        section.incorporate_node(value)
        return section

    def visit_section(self, node: PNode, children: SymlNodes) -> nodes.KeyValue:
        """Visit a key/value section."""
        key, _ = children
        return nodes.KeyValue(pnode=node, key=key)  # type: ignore[arg-type]

    def visit_list_item(self, node: PNode, children: SymlNodes) -> nodes.ListItem:
        """Visit a list item."""
        _, _, value = children
        li = nodes.ListItem(pnode=node)
        if value is not None:  # pragma: nobranch
            li.incorporate_node(value)
        return li

    def visit_lines(self, node: PNode, children: OptionalSymlNodes) -> nodes.Root:
        """Visit the lines within a SYML document."""
        root = nodes.Root(pnode=node)
        current: SymlNode = root

        for child in self.reduce_children(children):
            if isinstance(child, nodes.Comment):
                current.comments.append(child)
            else:
                current = current.incorporate_node(child)
        return root


def parse(source_syml: str) -> nodes.Root:
    """Parse a SYML document."""
    return SymlParser().parse(source_syml)
