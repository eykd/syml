"""Whole-document tests over realistic SYML fixtures (D18, D19).

The fixtures are interactive-fiction scripts: prose full of quotation marks
and apostrophes, and keys that are all lowercase. They pin down that quotes
are literal text and that a whole document round-trips through `dumps`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from syml import dumps, load, loads

if TYPE_CHECKING:  # pragma: nocover
    from syml.basetypes import SymlData

FIXTURES = Path(__file__).parent / 'fixtures'

STRANGER: SymlData = {
    'given': ['Charm = 3'],
    'stranger': [
        {'when': ['[Met Stranger] == 0']},
        'A tall figure stepped out of the rain and into the doorway.',
        '"You\'re late," she said, shaking water from her hat.',
        {'choice': '"I got held up."'},
        {'choice': ['"Late for what?"', '"Don\'t play games with me, Marlowe."']},
        {
            'choice': [
                '[Say nothing.]',
                '"Suit yourself," she said, and turned to go.',
                '{Charm > 2}"Wait," I said. She stopped.',
            ]
        },
        {'choice': '"Who\'s asking?" I said, reaching for my coat.'},
        '"Well?"',
    ],
}

BAR: SymlData = {
    'include': ['foyer'],
    'given': ['Fumbled = 0', 'Bar = 0'],
    'when': ['Location = "Bar"', '"Wearing Cloak" >= 1'],
    'look-in-dark': [
        "It is pitch dark[…], and you can't see a thing. It would be easy to trip\nover something.",
        {'effect': 'Bar += 1'},
    ],
    'fumble-around': [
        {'when': ['Bar >= 2']},
        '[Fumble around for a light switch.]You fumble around in the dark, but to no avail.',
        {'effect': 'Fumbled = 1'},
    ],
    'leave': [
        '[The bright opulence of the Foyer beckons you.]You leave the darkened Bar.',
        {'effect': ['Location = "Foyer"']},
    ],
}


def _load_fixture(name: str) -> SymlData:
    """Load `tests/fixtures/<name>.syml` through a binary handle."""
    with (FIXTURES / f'{name}.syml').open('rb') as file_obj:
        return load(file_obj)


class TestFixtureDocuments:
    """Each fixture loads to its full expected tree and round-trips through dumps."""

    @pytest.mark.parametrize(('name', 'expected'), [('stranger', STRANGER), ('bar', BAR)])
    def test_it_should_load_the_full_expected_tree(self, name: str, expected: SymlData) -> None:
        assert _load_fixture(name) == expected

    @pytest.mark.parametrize('name', ['stranger', 'bar'])
    def test_it_should_round_trip_the_loaded_tree_through_dumps(self, name: str) -> None:
        tree = _load_fixture(name)
        assert loads(dumps(tree)) == tree
