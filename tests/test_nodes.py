"""Tests for src/syml/nodes.py."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest

import syml
from syml import nodes, parsers
from syml.basetypes import Pos
from syml.exceptions import DuplicateKeyError, OutOfContextNodeError
from syml.parsers import SymlParser

if TYPE_CHECKING:
    from parsimonious.nodes import Node as PNode


def _pnode(text: str) -> PNode:
    """Build a real parsimonious node usable as a SymlNode's `pnode`."""
    return SymlParser.grammar['text'].parse(text)


class _BareSymlNode(nodes.SymlNode):
    """A `SymlNode` subclass with no overrides, for exercising the base class's own methods directly.

    Replaces the deleted `IndentNode` (Contract 01 §Coverage at the
    grammar-leaf commit): `SymlNode.as_data`/`as_source`/`can_add_node`/
    `fail_to_incorporate_node` must stay reachable without a pragma.
    """


class TestTextLeafNodeAnchorLevelAndBaseline:
    """Contract 03 §Where anchor_level and baseline are assigned (red-team pass 11).

    The visitor sets only `inline`; the **accepting node** sets
    `anchor_level` and `baseline` when it attaches the leaf: `anchor_level =
    self.level` and `baseline = None if node.inline else node.level`.
    """

    def test_container_node_add_node_sets_anchor_level_and_baseline_on_attach(self) -> None:
        """A ContainerNode (e.g. KeyValue) attaching a block-value leaf sets both fields."""
        key = nodes.KeyLeafNode(pnode=_pnode('key'))
        container = nodes.KeyValue(pnode=_pnode('key'), key=key, level=2)
        leaf = nodes.TextLeafNode(pnode=_pnode('value'), level=4)
        leaf.inline = False

        container.add_node(leaf)

        assert leaf.anchor_level == container.level
        assert leaf.baseline == leaf.level


class TestAcceptanceTableExactMatchSiblings:
    """Contract 03 §Acceptance table (§9.3): siblings match by level equality.

    `List` accepts only a `ListItem` whose level is exactly the list's own
    level (`node.level == self.level`), not merely `>=` it. A deeper
    candidate is not a new sibling; it must be declined here and re-offered
    up the parent chain (§9.2's walk-up), never silently absorbed as if it
    were level-aligned.
    """

    def test_list_declines_a_deeper_list_item_instead_of_accepting_it(self) -> None:
        """A ListItem deeper than the List's own level is not an exact-level sibling."""
        lst = nodes.List(pnode=_pnode('- a'), level=2)
        deeper_item = nodes.ListItem(pnode=_pnode('- a'), level=4)

        assert lst.can_add_node(deeper_item) is False


class TestTextLeafNodeContinuationBaseline:
    """Contract 03 §TextLeafNode continuation (§5.3, D11).

    Before the baseline is fixed (inline only), a candidate must have
    `level > anchor_level`. Once a continuation is accepted, its own level
    fixes the baseline. From then on, a candidate is accepted iff
    `level >= baseline`; a candidate below the baseline must be declined so
    it terminates the continuation and is re-offered up the parent chain.
    """

    def test_leaf_declines_a_continuation_candidate_below_its_fixed_baseline(self) -> None:
        """Once baseline is fixed by the first continuation, a shallower line is declined."""
        leaf = nodes.TextLeafNode(pnode=_pnode('a'), level=4)
        leaf.inline = True
        leaf.anchor_level = 2
        leaf.baseline = None

        first_continuation = nodes.TextLeafNode(pnode=_pnode('b'), level=6)
        assert leaf.can_add_node(first_continuation) is True
        leaf.add_node(first_continuation)
        assert leaf.baseline == 6

        below_baseline = nodes.TextLeafNode(pnode=_pnode('c'), level=2)
        assert leaf.can_add_node(below_baseline) is False


class TestAcceptsLevelTruthTable:
    """Contract 02 rule 2 / §Test obligations item 2: `accepts_level`'s full truth table.

    `False` for `None`. While `baseline` is unset (inline value awaiting its
    first continuation), the threshold is `anchor_level` and the comparison
    is strict (`>`): at or below is declined. Once `baseline` is fixed, the
    comparison is inclusive (`>=`): at or above is accepted, below declined.
    """

    def test_none_level_is_never_accepted(self) -> None:
        leaf = nodes.TextLeafNode(pnode=_pnode('a'), level=0)

        assert leaf.accepts_level(None) is False

    def test_unset_baseline_accepts_only_strictly_above_anchor_level(self) -> None:
        leaf = nodes.TextLeafNode(pnode=_pnode('a'), level=0)
        leaf.anchor_level = 2
        leaf.baseline = None

        assert leaf.accepts_level(3) is True
        assert leaf.accepts_level(2) is False
        assert leaf.accepts_level(1) is False

    def test_set_baseline_accepts_at_or_above_it(self) -> None:
        leaf = nodes.TextLeafNode(pnode=_pnode('a'), level=0)
        leaf.baseline = 4

        assert leaf.accepts_level(5) is True
        assert leaf.accepts_level(4) is True
        assert leaf.accepts_level(3) is False


class TestTextContextRereadsStructureShapedLines:
    """Contract 02 rule 1 (R-01, FR-003): a text tip re-reads a later structure-shaped line as text.

    `TextLeafNode.incorporate_node` swaps a candidate that lexed as
    structure (a `KeyValue`, `ListItem`, etc. carrying a `content_pnode`)
    for a fresh `TextLeafNode` built over that same `content_pnode`,
    whenever the candidate's level clears this leaf's threshold — before
    delegating to the normal accept/decline walk.
    """

    @staticmethod
    def _key_value_line(text: str) -> nodes.KeyValue:
        """Build a real `KeyValue` the way `visit_line` would, `content_pnode`/`level` included."""
        parser = SymlParser()
        line_pnode = SymlParser.grammar['line'].parse(text)
        return cast('nodes.KeyValue', parser.visit(line_pnode))

    def test_structure_shaped_candidate_at_or_past_threshold_is_rebuilt_as_text(self) -> None:
        """A KeyValue-shaped candidate within threshold becomes a TextLeafNode over content_pnode."""
        leaf = nodes.TextLeafNode(pnode=_pnode('prose'), level=0)
        leaf.baseline = 2
        candidate = self._key_value_line('  key: value')

        leaf.incorporate_node(candidate)

        rebuilt = leaf.children[-1]
        assert isinstance(rebuilt, nodes.TextLeafNode)
        assert rebuilt is not candidate
        assert rebuilt.pnode is candidate.content_pnode

    @staticmethod
    def _attach_to_root(leaf: nodes.TextLeafNode) -> None:
        """Parent `leaf` under a realistic `Root -> Mapping -> KeyValue` spine.

        So a rejected candidate's walk-up reaches `Root.fail_to_incorporate_node`
        with the `List`/`Mapping`-first-child invariant it assumes (Contract 03
        §Messages: "Root can only fail once its first child is a List or Mapping").
        """
        key_value = nodes.KeyValue(pnode=_pnode(''), key=nodes.KeyLeafNode(pnode=_pnode('k')), level=0)
        key_value.children = [leaf]
        leaf.parent = key_value
        mapping = nodes.Mapping(pnode=_pnode(''), level=0)
        mapping.children = [key_value]
        key_value.parent = mapping
        root = nodes.Root(pnode=_pnode(''))
        root.children = [mapping]
        mapping.parent = root

    def test_structure_shaped_candidate_below_threshold_is_not_rebuilt(self) -> None:
        """A candidate below threshold walks up unchanged, never swapped for text."""
        leaf = nodes.TextLeafNode(pnode=_pnode('prose'), level=0)
        leaf.baseline = 4
        self._attach_to_root(leaf)
        candidate = self._key_value_line('  key: value')

        with pytest.raises(OutOfContextNodeError):
            leaf.incorporate_node(candidate)

    def test_candidate_without_content_pnode_is_not_rebuilt(self) -> None:
        """A candidate carrying no content_pnode (not a whole-line lex) is left alone."""
        leaf = nodes.TextLeafNode(pnode=_pnode('prose'), level=0)
        leaf.baseline = 2
        self._attach_to_root(leaf)
        candidate = self._key_value_line('  key: value')
        candidate.content_pnode = None

        with pytest.raises(OutOfContextNodeError):
            leaf.incorporate_node(candidate)


class TestMappingDuplicateKeyDetection:
    """Contract 03 §Duplicate keys (FR-007, §8.3, §10.3).

    `Mapping.can_add_node` raises `DuplicateKeyError` immediately when a
    same-level `KeyValue` repeats an already-incorporated sibling's key,
    rather than silently accepting the second occurrence (today's
    behavior: the later value overwrites the earlier one in `as_data()`).
    """

    def test_mapping_raises_duplicate_key_error_for_repeated_key_at_same_level(self) -> None:
        """A second same-level KeyValue whose key repeats an existing child's key raises."""
        mapping = nodes.Mapping(pnode=_pnode('key: value1'), level=0)
        first_key = nodes.KeyLeafNode(pnode=_pnode('key'))
        first_kv = nodes.KeyValue(pnode=_pnode('key: value1'), key=first_key, level=0)
        mapping.add_node(first_kv)

        second_key = nodes.KeyLeafNode(pnode=_pnode('key'))
        second_kv = nodes.KeyValue(pnode=_pnode('key: value2'), key=second_key, level=0)

        with pytest.raises(DuplicateKeyError) as exc_info:
            mapping.can_add_node(second_kv)

        assert exc_info.value.key == 'key'
        assert exc_info.value.first_position == first_kv.source.start


class TestAutomaticContainerCreation:
    """Contract 03 §Automatic container creation (§9.4).

    Accepting a bare `KeyValue` inserts a `Mapping` intermediary at the
    incoming node's own level: `Mapping(source=node.source, level=node.level)`.
    The intermediary's `Source` is the triggering node's own `Source` — its
    `filename` in particular — not one rebuilt from the accepting container's
    `filename`.
    """

    def test_auto_created_mapping_carries_the_triggering_nodes_filename(self) -> None:
        """The auto-created Mapping's Source.filename matches the KeyValue's, not the Root's."""
        root = nodes.Root(pnode=_pnode(''))
        key = nodes.KeyLeafNode(pnode=_pnode('key'), filename='doc.syml')
        kv = nodes.KeyValue(pnode=_pnode('key: value'), key=key, level=0, filename='doc.syml')

        root.incorporate_node(kv)

        intermediary = root.children[0]
        assert isinstance(intermediary, nodes.Mapping)
        assert intermediary.source.filename == kv.source.filename


class TestChildlessRootYieldsEmptyString:
    """Contract 03 §Absent values (FR-005): empty and comment-only documents yield "".

    A childless `Root` is a `ContainerNode` with no children, so its
    `as_data()` must return `''` rather than `None` (US4, no `loads`/`load`
    result may contain `None` at any depth).
    """

    def test_childless_root_as_data_is_empty_string_not_none(self) -> None:
        """A Root with no children (empty or comment-only document) returns ''."""
        root = nodes.Root(pnode=_pnode(''))

        assert root.as_data() == ''


class TestValuelessKeyYieldsEmptyStringAtEveryDepth:
    """Contract 03 §Absent values (FR-005): a childless key yields "" at any depth.

    `ContainerNode.as_data` (the base `KeyValue` uses) still returns `None`
    when childless — only `Root` overrides it. The invariant is stated in
    `loads` terms: no result may contain `None` at any depth (US4 scenario
    5), so a valueless key nested two levels deep, and one alongside a
    populated sibling, must also come back as `''`.
    """

    def test_valueless_key_yields_empty_string_at_every_depth(self) -> None:
        """A childless key at depth 0, 1, and 2 all yield '', never None."""
        document = 'top:\n  mid:\n    deep:\n  sib:\nafter:\n'

        result = syml.loads(document)

        assert result == {
            'top': {'mid': {'deep': ''}, 'sib': ''},
            'after': '',
        }


def _assert_no_null_leaves(value: object) -> None:
    """Recursively walk `value`, failing if any leaf (non-dict/list) is None."""
    if isinstance(value, dict):
        for item in value.values():
            _assert_no_null_leaves(item)
    elif isinstance(value, list):
        for item in value:
            _assert_no_null_leaves(item)
    else:
        assert value is not None


class TestNoLeafOfAnyAcceptedDocumentIsEverANull:
    """Contract 03 §Worked cases: no leaf of an accepted document is ever `None`.

    US4 scenario 5 states the invariant in `loads` terms (`as_data`), and
    it already holds there. But `ContainerNode.as_source` — the sibling
    rendering used for `Source`-carrying output — still returns `None` for
    a childless container (nodes.py's `as_source` docstring/branch), so the
    same recursive walk over `as_source()` output finds a null leaf where a
    valueless key's value should be an empty `Source`.
    """

    @pytest.mark.parametrize(
        'document',
        [
            'a:\n',
            'top:\n  mid:\n    deep:\n  sib:\nafter:\n',
            '- \n- \n',
        ],
    )
    def test_as_source_never_yields_a_null_leaf(self, document: str) -> None:
        """Walking `as_source()` for accepted documents never finds a None leaf."""
        root = parsers.parse(document)

        _assert_no_null_leaves(root.as_source())


class TestSymlNodeBaseStubs:
    """Contract 08 §Coverage / Contract 03 §Coverage without pragmas (FR-012).

    `SymlNode`'s undecorated `as_data`/`as_source`/`can_add_node`/
    `incorporate_node` failure path are reachable directly through a bare
    subclass with no overrides, since the grammar leaf deletes `IndentNode`.
    """

    def test_as_data_raises_not_implemented(self) -> None:
        node = _BareSymlNode(pnode=_pnode('  '))

        with pytest.raises(NotImplementedError):
            node.as_data()

    def test_as_source_raises_not_implemented(self) -> None:
        node = _BareSymlNode(pnode=_pnode('  '))

        with pytest.raises(NotImplementedError):
            node.as_source()

    def test_can_add_node_rejects_by_default(self) -> None:
        node = _BareSymlNode(pnode=_pnode('  '))
        other = _BareSymlNode(pnode=_pnode('  '))

        assert node.can_add_node(other) is False

    def test_incorporate_node_fails_when_parentless_and_rejected(self) -> None:
        """The base-class `fail_to_incorporate_node` stub is a plain `NotImplementedError`.

        Contract 03 §Placement: only `Root` builds the real
        `OutOfContextNodeError` description — a non-`Root` node, such as
        this bare, parentless `_BareSymlNode`, never reaches this path in a
        real parse (every other node type is attached to a parent the
        moment it exists), so the base stub stays a `NotImplementedError`
        rather than duplicating `Root`'s message-building logic.
        """
        node = _BareSymlNode(pnode=_pnode('  '))
        other = _BareSymlNode(pnode=_pnode('  '))

        with pytest.raises(NotImplementedError):
            node.incorporate_node(other)


class TestRootScalarKeepsIndentation:
    """Contract 02 rule 5 (R-12, US1-10, US1-14, US1-25 half, `syml-xreq.2`).

    An empty `Root` offered a plain, non-inline `TextLeafNode` rebuilds it
    over `line_pnode` (the whole physical line, indentation included) rather
    than the grammar's `text` pnode, and fixes its `baseline` at 0 — a root
    scalar keeps its own leading indentation as literal characters instead
    of having it stripped like a nested value's anchor column would.
    """

    def test_root_incorporate_node_rebuilds_an_indented_first_line_over_line_pnode(self) -> None:
        """An empty Root offered an indented plain-text line keeps the leading spaces."""
        root = nodes.Root(pnode=_pnode(''))
        line_node = SymlParser.grammar['line'].parse('  hello')
        value = nodes.TextLeafNode(pnode=_pnode('hello'), line_pnode=line_node, level=2)

        root.incorporate_node(value)

        rebuilt = cast('nodes.TextLeafNode', root.children[0])
        assert rebuilt.source.text == '  hello'
        assert rebuilt.baseline == 0

    def test_root_incorporate_node_leaves_an_inline_leaf_unrebuilt(self) -> None:
        """A `TextLeafNode` already marked inline is not rebuilt (rule 5 only covers bare lines)."""
        root = nodes.Root(pnode=_pnode(''))
        line_node = SymlParser.grammar['line'].parse('  hello')
        value = nodes.TextLeafNode(pnode=_pnode('hello'), line_pnode=line_node, level=2, inline=True)

        root.incorporate_node(value)

        assert root.children[0] is value
        assert root.children[0].source.text == 'hello'

    def test_root_incorporate_node_leaves_a_leaf_without_line_pnode_unrebuilt(self) -> None:
        """A `TextLeafNode` with no `line_pnode` (not a whole-line lex) is not rebuilt."""
        root = nodes.Root(pnode=_pnode(''))
        value = nodes.TextLeafNode(pnode=_pnode('hello'), level=2)

        root.incorporate_node(value)

        assert root.children[0] is value
        assert root.children[0].source.text == 'hello'

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            ('  hello', '  hello'),
            ('  hello\nworld', '  hello\nworld'),
            ('  hello\n    world', '  hello\n    world'),
            ('# c\n  hello', '  hello'),
        ],
    )
    def test_an_indented_root_scalar_keeps_its_indentation(self, text: str, expected: str) -> None:
        assert syml.loads(text) == expected

    def test_an_indented_root_scalars_source_starts_at_column_0(self) -> None:
        assert parsers.parse('  hello').as_source().start == Pos(0, 1, 0)


class TestBlankAndCommentOnlyDocumentSourceStart:
    r"""Contract 05 §Behaviour: a blank-only or comment-only document ending in `\n` (`syml-xreq.11`).

    Both are zero-width under the empty-document/column-0-comment rules, so
    `.as_source().start` must report a `Pos` consistent with the end-of-text
    fix in `Pos.from_str_index` -- the *next* line, column 0 -- not the line
    that ended.
    """

    def test_a_blank_only_document_reports_the_next_line_column_zero(self) -> None:
        assert parsers.parse('\n').as_source().start == Pos(index=1, line=2, column=0)

    def test_a_comment_only_document_reports_the_next_line_column_zero(self) -> None:
        assert parsers.parse('# x\n').as_source().start == Pos(index=4, line=2, column=0)

    def test_an_empty_document_still_reports_the_first_line_column_zero(self) -> None:
        assert parsers.parse('').as_source().start == Pos(index=0, line=1, column=0)
