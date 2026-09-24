"""Tests for src/syml/nodes.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from syml import nodes
from syml.parsers import SymlParser

if TYPE_CHECKING:
    from parsimonious.nodes import Node as PNode


def _pnode(text: str) -> PNode:
    """Build a real parsimonious node usable as a SymlNode's `pnode`."""
    return SymlParser.grammar['text'].parse(text)


class TestTextLeafNodeAnchorLevelAndBaseline:
    """Contract 03 §Where anchor_level and baseline are assigned (red-team pass 11).

    The visitor sets only `inline`/`quoted`; the **accepting node** sets
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
