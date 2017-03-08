from parsimonious import NodeVisitor, Grammar, VisitationError

from . import grammars
from . import nodes
from .exceptions import OutOfContextNodeError


class TextOnlySymlParser(NodeVisitor):
    grammar = Grammar(grammars.text_only_syml_grammar)

    def reduce_children(self, children):
        children = [c for c in children if c is not None]
        if children:
            return children if len(children) > 1 else children[0]
        else:
            return None

    def visit_blank(self, node, children):
        return None

    def visit_line(self, node, children):
        indent, value, _ = children
        if value is not None:
            value.level = indent
            return value

    def generic_visit(self, node, children):
        return self.reduce_children(children)

    def get_text(self, node, children):
        return nodes.TextLeafNode(node, node.text)

    def visit_comment(self, node, children):
        _, text = children
        return nodes.Comment(text)

    visit_text = get_text
    visit_key = get_text

    def visit_indent(self, node, children):
        return len(node.text.replace('\t', ' ' * 4).strip('\n'))

    def visit_key_value(self, node, children):
        section, _, value = children
        section.incorporate_node(value)
        return section

    def visit_section(self, node, children):
        key, _ = children
        return nodes.KeyValue(node, key)

    def visit_list_item(self, node, children):
        _, _, value = children
        li = nodes.ListItem(node)
        li.incorporate_node(value)
        return li

    def visit_lines(self, node, children):
        root = nodes.Root(node)
        current = root

        children = self.reduce_children(children)
        if isinstance(children, nodes.LeafNode):
            children = [children]

        for child in children:
            if isinstance(child, nodes.Comment):
                current.comments.append(child)
            else:
                current = current.incorporate_node(child)
        return root

    def parse(self, *args, **kwargs):
        try:
            return super().parse(*args, **kwargs)
        except VisitationError as e:
            # Parsimonious swallows errors inside of `visit_` handlers and
            # wraps them in VisitationError cruft.
            if e.args[0].startswith('OutOfContextNodeError'):
                # Extract the original error message, ignoring the cruft.
                msg = e.args[0].split('\n\n\n')[0].split(':', 1)[1]
                raise OutOfContextNodeError(msg)
            else:
                raise  # pragma: no cover


class BooleanSymlParser(TextOnlySymlParser):
    """Syml with support for YAML-like boolean values.
    """
    grammar = Grammar(grammars.boolean_syml_grammar)

    def visit_truthy(self, node, children):
        return nodes.RawValueLeafNode(node, node.text, value=True)

    def visit_falsey(self, node, children):
        return nodes.RawValueLeafNode(node, node.text, value=False)


def parse(source_syml, filename='', raw=True, booleans=False):
    parser = BooleanSymlParser if booleans else TextOnlySymlParser
    return parser().parse(source_syml).as_data(filename, raw=raw)
