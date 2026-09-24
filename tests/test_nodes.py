"""Tests for src/syml/nodes.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import syml
from syml import nodes, parsers
from syml.exceptions import DuplicateKeyError, OutOfContextNodeError
from syml.parsers import SymlParser

if TYPE_CHECKING:
    from parsimonious.nodes import Node as PNode


def _pnode(text: str) -> PNode:
    """Build a real parsimonious node usable as a SymlNode's `pnode`."""
    return SymlParser.grammar['text'].parse(text)


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


class TestDirectTestsForPreviouslyPragmadBranches:
    """Contract 03 §Coverage without pragmas (red-team pass 23).

    `Comment.as_data`/`can_add_node` are pragma'd dead code: the per-line
    visitor loop routes comments to `tip.comments` (Contract 02), so no
    `loads` input ever calls them. The contract's disposition deletes both
    overrides, leaving `Comment` inherit `TextLeafNode.as_data` (the joined
    source text) instead of always returning `''`.
    """

    def test_comment_as_data_is_inherited_from_text_leaf_node(self) -> None:
        """Comment.as_data is deleted (§Coverage without pragmas); it inherits TextLeafNode's."""
        comment = nodes.Comment(pnode=_pnode('note'))

        assert comment.as_data() == 'note'


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
    `incorporate_node` failure path are reachable directly through a
    subclass with no overrides (`IndentNode`) rather than pragma'd as dead.
    """

    def test_as_data_raises_not_implemented(self) -> None:
        node = nodes.IndentNode(pnode=_pnode('  '))

        with pytest.raises(NotImplementedError):
            node.as_data()

    def test_as_source_raises_not_implemented(self) -> None:
        node = nodes.IndentNode(pnode=_pnode('  '))

        with pytest.raises(NotImplementedError):
            node.as_source()

    def test_can_add_node_rejects_by_default(self) -> None:
        node = nodes.IndentNode(pnode=_pnode('  '))
        other = nodes.IndentNode(pnode=_pnode('  '))

        assert node.can_add_node(other) is False

    def test_incorporate_node_fails_when_parentless_and_rejected(self) -> None:
        node = nodes.IndentNode(pnode=_pnode('  '))
        other = nodes.IndentNode(pnode=_pnode('  '))

        with pytest.raises(OutOfContextNodeError):
            node.incorporate_node(other)
