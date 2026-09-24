"""SYML parsers"""

from __future__ import annotations

import dataclasses
import textwrap
from typing import TYPE_CHECKING

from parsimonious import Grammar, NodeVisitor
from parsimonious.nodes import Node

from . import nodes, quoting
from .basetypes import Pos
from .exceptions import MalformedQuotedStringError, ParseError, error_message
from .preprocess import preprocess
from .utils import get_line_text

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

            key_value          = quoted_key_value / data_key_value
            quoted_key_value   = section ws? quoted_value ~" *"
            data_key_value     = section ws data
            section     = key ":"
            key         = ~"[^\s:\x00-\x1f\x7f-\x9f]+"   # Printable, non-whitespace, non-colon (§4.5's \s is the Unicode White_Space set)

            eol         = "\n" / ~"$"
            ws          = ~" +"   # Required whitespace (spaces only; a tab does not satisfy this, see §7.5)
            text        = ~"[^\n]*"

            value       = structure / data
            data        = text

            quoted_value  = single_quoted / double_quoted
            single_quoted = "'" ~"(?:''|[^'\n])*" "'"
            # §4.7 escape table: \n \t \r \\ \/ \" \uXXXX \UXXXXXXXX. An invalid or
            # incomplete escape fails to match here, so the line falls through to the
            # quote-guard (R-10) instead of silently decoding.
            double_quoted = "\"" ~"(?:\\\\(?:[\\\\/\"ntr]|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8})|[^\"\\\\\n])*" "\""

            """
        )
    )
    unwrapped_exceptions = (ParseError,)

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

    def visit_line(self, node: Node, children: SymlNodes) -> OptionalNodes:  # noqa: ARG002
        """Visit a line."""
        _indent, value, _eol = children
        if value is not None:
            # R-11: level comes from the node's own column (set at
            # construction from its own `pnode.start`), not the line's
            # `indent` token — no longer applied here.
            return value
        return None

    def generic_visit(self, node: Node, children: OptionalSymlNodes) -> SymlNodes | SymlNode | None:  # type: ignore[override]  # noqa: ARG002
        """Visit a generic node."""
        nodes = self.reduce_children(children)
        if not nodes:
            return None
        if len(nodes) == 1:
            return nodes[0]
        else:  # pragma: nocover  # noqa: RET505
            return nodes

    def visit_text(self, node: Node, children: SymlNodes) -> nodes.TextLeafNode:  # noqa: ARG002
        """Return a text leaf node."""
        return nodes.TextLeafNode(pnode=node, filename=self.filename)

    def visit_single_quoted(self, node: Node, children: SymlNodes) -> nodes.TextLeafNode:
        """Decode a single-quoted inline value (D2).

        Parsimonious collapses the `quoted_value = single_quoted` alias, so
        the grammar's actual match node is named `single_quoted`, not
        `quoted_value`; `visit_quoted_value` stays for the synthetic-node
        tests that construct a `quoted_value`-named node directly.
        """
        return self.visit_quoted_value(node, children)

    def _malformed_quoted_string(
        self, pnode: Node, *, escape: str | None, code_point: int | None
    ) -> MalformedQuotedStringError:
        """Build a `MalformedQuotedStringError` anchored at `pnode`'s position.

        Shared by `visit_quoted_value` (a decoder defect on a value that matched
        `quoted_value`) and `visit_data_key_value` (the quote-guard rule, R-10:
        a value that looks quoted but fell through to `data` instead).
        """
        position = Pos.from_str_index(pnode.full_text, pnode.start)
        return MalformedQuotedStringError(
            error_message('Malformed quoted string', self.filename),
            position,
            get_line_text(pnode.full_text, position.line),
            escape=escape,
            code_point=code_point,
        )

    def visit_quoted_value(self, node: Node, children: SymlNodes) -> nodes.TextLeafNode:  # noqa: ARG002
        """Decode a quoted inline value, converting a decoder defect to `MalformedQuotedStringError`.

        `decode_double_quoted` is position-free (Contract 04), so the
        position is anchored here, at the opening quote, from `node` itself.
        """
        raw = node.text
        try:
            text = quoting.decode_single_quoted(raw) if raw.startswith("'") else quoting.decode_double_quoted(raw)
        except quoting.QuotedStringDefect as defect:
            raise self._malformed_quoted_string(node, escape=defect.escape, code_point=defect.code_point) from defect
        leaf = nodes.TextLeafNode(pnode=node, filename=self.filename, quoted=True, inline=True)
        source = leaf.source
        if self.position_map is not None:
            source = dataclasses.replace(
                source,
                start=self.position_map.to_original(source.start),
                end=self.position_map.to_original(source.end),
            )
        leaf.source = dataclasses.replace(source, text=text)
        return leaf

    def visit_key(self, node: Node, children: SymlNodes) -> nodes.KeyLeafNode:  # noqa: ARG002
        """Return a key leaf node."""
        return nodes.KeyLeafNode(pnode=node, filename=self.filename)

    def visit_comment(self, node: Node, children: SymlNodes) -> nodes.Comment:
        """Visit a comment node.

        The trailing `text?` is optional (FR-009): a comment-only line whose
        markers consume the whole line (e.g. '####') leaves it unmatched, so
        parsimonious visits it to `None` rather than a zero-length node.
        Synthesize a zero-width node at the comment's own end position
        instead of dereferencing `.pnode` on `None`.
        """
        _, text = children
        text_pnode = text.pnode if text is not None else Node(node.expr, node.full_text, node.end, node.end)
        return nodes.Comment(pnode=text_pnode, filename=self.filename)

    def visit_indent(self, node: Node, children: SymlNodes) -> nodes.IndentNode:  # noqa: ARG002
        """Visit an indentation token."""
        return nodes.IndentNode(
            pnode=node, level=len(node.text.replace('\t', ' ' * 4).strip('\n')), filename=self.filename
        )

    def visit_data_key_value(self, node: Node, children: SymlNodes) -> OptionalNodes:  # noqa: ARG002
        """Visit a mapping value whose data is unquoted text.

        The quote-guard rule (§4.1, R-10): `data` beginning with `'` or `"` means
        `quoted_value` failed to match and the line fell through here instead of
        raising. Diagnose the fallthrough and raise rather than keep the leading
        quote as text (Contract 04 §The quote-guard rule).
        """
        section, _, value = children
        text = value.source.text
        if text[:1] in ("'", '"'):
            raise self._malformed_quoted_string(value.pnode, escape=quoting.diagnose_malformed(text), code_point=None)
        if not _is_zero_length_text(value):
            _mark_inline(value)
            section.incorporate_node(value)
        return section

    def visit_quoted_key_value(self, node: Node, children: SymlNodes) -> OptionalNodes:  # noqa: ARG002
        """Visit a mapping value at an inline quoted position (D2)."""
        section, _ws, value, _trailing = children
        section.incorporate_node(value)
        return section

    def visit_section(self, node: Node, children: SymlNodes) -> nodes.KeyValue:
        """Visit a key/value section."""
        key, _ = children
        return nodes.KeyValue(pnode=node, key=key, filename=self.filename)  # type: ignore[arg-type]

    def visit_value_list_item(self, node: Node, children: SymlNodes) -> nodes.ListItem:
        """Visit a list item carrying an inline value."""
        _, _, value = children
        li = nodes.ListItem(pnode=node, filename=self.filename)
        if value is not None and not _is_zero_length_text(value):  # pragma: nobranch
            _mark_inline(value)
            li.incorporate_node(value)
        return li

    def visit_guard_list_item(self, node: Node, children: SymlNodes) -> nodes.ListItem:  # noqa: ARG002
        """Visit a bare list item whose value comes from a nested block."""
        return nodes.ListItem(pnode=node, filename=self.filename)

    def visit_lines(self, node: Node, children: OptionalSymlNodes) -> nodes.Root:
        """Visit the lines within a SYML document."""
        root = nodes.Root(pnode=node, filename=self.filename)
        current: SymlNode = root

        for child in self.reduce_children(children):
            if isinstance(child, nodes.Comment):
                current.comments.append(child)
            else:
                current = current.incorporate_node(child)
        return root


def find_first(node: Node, expr_name: str) -> Node:
    """Depth-first search of `node` and its descendants for the first with a matching `expr_name`.

    Parsimonious's `Node` has no such method; Contract 05 §The third-party
    boundary (FR-009, R-09) defines this helper so `raise_trailing_content`
    can locate the `quoted_value` node that anchors a stranded-content error.

    :param node: The root of the subtree to search.
    :param expr_name: The `expr_name` to match.
    :returns: The first matching node, in depth-first order.
    """
    stack = [node]
    while True:
        current = stack.pop()
        if current.expr_name == expr_name:
            return current
        stack.extend(reversed(current.children))


def parse(source_syml: str, filename: StrPath | None = None) -> nodes.Root:
    """Parse a SYML document."""
    doc = preprocess(source_syml, filename)
    return SymlParser(filename=filename, position_map=doc.position_map).parse(doc.normalized)
