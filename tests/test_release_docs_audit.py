"""Regression pins for the Contract 06 / Contract 03 audit-text fixes (`syml-cjk2.27`).

`specs/002-syml-language-revision/contracts/06-release-text.md`'s §C audit
list and Contract 03's amendment header drifted from the code and from each
other during break-testing round 2: item 27's paragraph still described the
superseded 80-code-point head-centered filename window instead of D34's
tail window, item 34 (D35) had no paragraph at all, the item 25/26
paragraph claimed no README change happened when D26 and D27 both edited
README.md, and Contract 03's header omitted D34 even though its own
§Bounded rendering section documents D34's change. These tests fail if any
of those four corrections is reverted.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONTRACT_06 = _REPO_ROOT / 'specs' / '002-syml-language-revision' / 'contracts' / '06-release-text.md'
_CONTRACT_03 = _REPO_ROOT / 'specs' / '002-syml-language-revision' / 'contracts' / '03-errors.md'


def test_contract_03_header_cites_d34() -> None:
    """Contract 03's amendment header lists D34 alongside the other break-test-round-2 decisions."""
    header = _CONTRACT_03.read_text(encoding='utf-8').splitlines()[2]
    assert 'D34' in header, 'expected Contract 03 line 3 to cite D34 (its §Bounded rendering change)'


def test_contract_06_item_27_describes_d34s_tail_window() -> None:
    """Item 27's audit paragraph names D34 and the tail-windowing fix, not the superseded head window."""
    text = _CONTRACT_06.read_text(encoding='utf-8')
    start = text.index('item 27,')
    paragraph = text[start : text.index('\n\n', start)]
    assert 'D34' in text[max(0, start - 80) : start], 'expected item 27 to be introduced as a D34 paragraph'
    assert 'tail' in paragraph, "expected item 27's paragraph to describe the tail-windowing fix"
    assert '1024' in paragraph, "expected item 27's paragraph to state the 1024-code-point bound"


def test_contract_06_has_an_item_34_audit_paragraph() -> None:
    """Item 34 (D35, the scheme:// exclusion from hint (c)) has its own audit paragraph."""
    text = _CONTRACT_06.read_text(encoding='utf-8')
    assert 'item 34,' in text, 'expected a §C audit paragraph for item 34'
    start = text.index('item 34,')
    paragraph = text[max(0, start - 90) : text.index('\n\n', start)]
    assert 'D35' in paragraph
    assert 'scheme' in paragraph


def test_contract_06_item_25_26_paragraph_names_the_actual_readme_changes() -> None:
    """The item 25/26 paragraph states what D26/D27 actually changed in README.md, not a blanket denial."""
    text = _CONTRACT_06.read_text(encoding='utf-8')
    start = text.index('Item 25 (D26')
    paragraph = text[start : text.index('\n\n', start)]
    assert 'no README change for either' not in paragraph
    assert 'bullet 7' in paragraph
    assert 'bullets 1 and 3' in paragraph
