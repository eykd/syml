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
