from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Union

from parsimonious import Grammar, NodeVisitor, VisitationError

from . import grammars, nodes
from .exceptions import OutOfContextNodeError

if TYPE_CHECKING:
    from parsimonious.nodes import Node as PNode

    from .types import StrPath


YamlNodes = Iterable[Optional[nodes.YamlNode]]

NodeOrNodes = Union[YamlNodes, nodes.YamlNode]


OptionalNodes = Optional[NodeOrNodes]


class TextOnlySymlParser(NodeVisitor):
    grammar = Grammar(grammars.text_only_syml_grammar)

    def reduce_children(self, children: YamlNodes) -> OptionalNodes:
        children = [c for c in children if c is not None]
        if children:
            return children if len(children) > 1 else children[0]
        else:
            return None

    def visit_blank(self, node: PNode, children: YamlNodes) -> None:
        return None

    def visit_line(self, node: PNode, children: YamlNodes) -> OptionalNodes:
        indent, value, _ = children
        if value is not None:
            value.level = indent
            return value

    def generic_visit(self, node: PNode, children: YamlNodes) -> OptionalNodes:
        return self.reduce_children(children)

    def get_text(self, node: PNode, children: YamlNodes) -> nodes.TextLeafNode:
        return nodes.TextLeafNode(node, node.text)

    def visit_comment(self, node: PNode, children: YamlNodes) -> nodes.Comment:
        _, text = children
        return nodes.Comment(text)

    visit_text = get_text
    visit_key = get_text

    def visit_indent(self, node: PNode, children: YamlNodes) -> int:
        return len(node.text.replace("\t", " " * 4).strip("\n"))

    def visit_key_value(self, node: PNode, children: YamlNodes) -> OptionalNodes:
        section, _, value = children
        section.incorporate_node(value)
        return section

    def visit_section(self, node: PNode, children: YamlNodes) -> nodes.KeyValue:
        key, _ = children
        return nodes.KeyValue(node, key)

    def visit_list_item(self, node: PNode, children: YamlNodes) -> nodes.ListItem:
        _, _, value = children
        li = nodes.ListItem(node)
        li.incorporate_node(value)
        return li

    def visit_lines(self, node: PNode, children: YamlNodes) -> nodes.Root:
        root = nodes.Root(node)
        current = root

        children = self.reduce_children(children)
        if isinstance(children, nodes.YamlNode):
            children = [children]

        for child in children:
            if isinstance(child, nodes.Comment):
                current.comments.append(child)
            else:
                current = current.incorporate_node(child)
        return root

    def parse(self, *args, **kwargs) -> PNode:
        try:
            return super().parse(*args, **kwargs)
        except VisitationError as e:
            # Parsimonious swallows errors inside of `visit_` handlers and
            # wraps them in VisitationError cruft.
            if e.args[0].startswith("OutOfContextNodeError"):
                # Extract the original error message, ignoring the cruft.
                msg = e.args[0].split("\n\n\n")[0].split(":", 1)[1]
                raise OutOfContextNodeError(msg)
            else:
                raise  # pragma: no cover


class BooleanSymlParser(TextOnlySymlParser):
    """Syml with support for YAML-like boolean values."""

    grammar = Grammar(grammars.boolean_syml_grammar)

    def visit_truthy(self, node: PNode, children: YamlNodes) -> nodes.RawValueLeafNode:
        return nodes.RawValueLeafNode(node, node.text, value=True)

    def visit_falsey(self, node: PNode, children: YamlNodes) -> nodes.RawValueLeafNode:
        return nodes.RawValueLeafNode(node, node.text, value=False)


def parse(
    source_syml: str, filename: StrPath = "", raw: bool = True, booleans: bool = False
) -> Union[List, Dict, str, bool]:
    parser = BooleanSymlParser if booleans else TextOnlySymlParser
    return parser().parse(source_syml).as_data(filename, raw=raw)
