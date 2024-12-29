"""SYML parsers"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from parsimonious import Grammar, NodeVisitor, VisitationError

from . import basetypes as types
from . import grammars, nodes
from .exceptions import OutOfContextNodeError

if TYPE_CHECKING:  # pragma: nocover
    from parsimonious.nodes import Node as PNode

    from .basetypes import StrPath
    from .nodes import OptionalNodes, OptionalSymlNodes, SymlNode, SymlNodes


class TextOnlySymlParser(NodeVisitor):  # type: ignore[type-arg]
    """Parser for the SYML variant that allows only text leaf nodes"""

    grammar = Grammar(grammars.text_only_syml_grammar)

    def reduce_children(self, children: OptionalSymlNodes) -> SymlNodes:
        """Return all non-null children."""
        return [c for c in children if c is not None]

    def visit_blank(self, node: PNode, children: OptionalSymlNodes) -> None:  # noqa: ARG002
        """Visit a blank."""
        return

    def visit_line(self, node: PNode, children: OptionalSymlNodes) -> OptionalNodes:  # noqa: ARG002
        """Visit a line."""
        indent, value, _ = children
        if value is not None:
            value.set_level(indent)  # type: ignore[arg-type]
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

    def get_text(self, node: PNode, children: OptionalSymlNodes) -> nodes.TextLeafNode:  # noqa: ARG002
        """Return a text leaf node."""
        return nodes.TextLeafNode(pnode=node, source_text=types.Source.from_node(node))

    def visit_comment(self, node: PNode, children: OptionalSymlNodes) -> nodes.Comment:
        """Visit a comment node."""
        _, text = children
        return nodes.Comment(pnode=node, value=text)

    visit_text = get_text
    visit_key = get_text

    def visit_indent(self, node: PNode, children: OptionalSymlNodes) -> int:  # noqa: ARG002
        """Visit an indentation token."""
        return len(node.text.replace('\t', ' ' * 4).strip('\n'))

    def visit_key_value(self, node: PNode, children: SymlNodes) -> OptionalNodes:  # noqa: ARG002
        """Visit a mapping value."""
        section, _, value = children
        section.incorporate_node(value)
        return section

    def visit_section(self, node: PNode, children: OptionalSymlNodes) -> nodes.KeyValue:
        """Visit a key/value section."""
        key, _ = children
        return nodes.KeyValue(pnode=node, key=key)

    def visit_list_item(self, node: PNode, children: OptionalSymlNodes) -> nodes.ListItem:
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

    def parse(self, *args: Any, **kwargs: Any) -> SymlNode:  # noqa: ANN401
        """Parse a SYML document."""
        try:
            return super().parse(*args, **kwargs)
        except VisitationError as exc:
            # Parsimonious swallows errors inside of `visit_` handlers and
            # wraps them in VisitationError cruft.
            if exc.args[0].startswith('OutOfContextNodeError'):
                # Extract the original error message, ignoring the cruft.
                msg = exc.args[0].split('\n\n\n')[0].split(':', 1)[1]
                raise OutOfContextNodeError(msg) from exc
            raise  # pragma: no cover


class BooleanSymlParser(TextOnlySymlParser):
    """Syml with support for YAML-like boolean values."""

    grammar = Grammar(grammars.boolean_syml_grammar)

    def visit_truthy(self, node: PNode, children: OptionalSymlNodes) -> nodes.RawValueLeafNode:  # noqa: ARG002
        """Visit a truthy value."""
        return nodes.RawValueLeafNode(pnode=node, source_text=types.Source.from_node(node), value=True)

    def visit_falsey(self, node: PNode, children: OptionalSymlNodes) -> nodes.RawValueLeafNode:  # noqa: ARG002
        """Visit a falsey value."""
        return nodes.RawValueLeafNode(pnode=node, source_text=types.Source.from_node(node), value=False)


def parse(
    source_syml: str,
    filename: StrPath = '',
    raw: bool = True,  # noqa: FBT001, FBT002
    booleans: bool = False,  # noqa: FBT001, FBT002
) -> list[Any] | dict[str, Any] | str | bool:
    """Parse a SYML document."""
    parser = BooleanSymlParser if booleans else TextOnlySymlParser
    return parser().parse(source_syml).as_data(filename, raw=raw)
