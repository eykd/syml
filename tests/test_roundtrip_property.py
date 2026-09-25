"""Round-trip property tests (Contract 04 §Test obligations, SC-002, R-14).

Ported from `specs/002-syml-language-revision/reference/lane-1-roundtrip-probe.py`
(the planning spike, "lane 1") for the revised grammar. The spike's
`FILTER_KNOWN`/`known_family` known-failure filter is **removed**: every
property here runs against the full generated input space. A property that
finds a real counterexample is a bug in `src/`, not a candidate for a new
filter (plan.md R-15; the P8 spike run held with no exclusion at 20,000
examples).

Hypothesis settings come from the `gate`/`fuzz` profiles registered in
`tests/conftest.py`. `just fuzz` runs this module under the `fuzz` profile.
"""

from __future__ import annotations

import operator
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from hypothesis import event, given
from hypothesis import strategies as st

import syml
from syml import serializer
from syml.exceptions import ParseError, UnrepresentableValueError

if TYPE_CHECKING:
    from syml.basetypes import SymlData

# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------

#: Unicode White_Space per spec §4.5 (mirrors the probe's WHITE_SPACE set).
_WHITE_SPACE = frozenset('\t\n\x0b\x0c\r \x85\xa0\u1680\u2028\u2029\u202f\u205f\u3000') | {
    chr(c) for c in range(0x2000, 0x200B)
}

#: A grab-bag of fragments likely to sit on a grammar edge: markers, keys,
#: comment sigils, quote/backslash text, BOM/NBSP/other-whitespace leads,
#: control characters, and a lone surrogate.
_SEED_FRAGMENTS = [
    '\ufeff',
    '\xa0',
    ' ',
    '\u3000',
    '\x85',
    '\u2028',
    '\x0c',
    '\x0b',
    '\x1c',
    '\x1d',
    '\x1e',
    '\x1f',
    '\U0001f600',
    '\t',
    '  ',
    '-',
    '- ',
    '- -',
    '#',
    '//',
    'key:',
    'key: ',
    'Key: ',
    ':',
    'k:v',
    '- k: ',
    '-\t',
    '\u200b',
    '\x00',
    '\x7f',
    '\x9f',
    "'",
    '"',
]
_BODY_ALPHABET = st.characters(exclude_characters='\n') | st.sampled_from([
    *'ab -:#/\t',
    *(c for c in _SEED_FRAGMENTS if len(c) == 1),
])
_body = st.text(alphabet=_BODY_ALPHABET, max_size=8)
_seeded_line = st.tuples(st.sampled_from([*_SEED_FRAGMENTS, *([''] * 8)]), _body).map(''.join)
_seeded_scalar = st.lists(_seeded_line, min_size=0, max_size=4).map('\n'.join)
_plain_scalar = st.text(max_size=12)
_punctuation_scalar = st.text(alphabet='abc XYZ-:#/\n\t\'"', max_size=12)
scalar = st.one_of(_seeded_scalar, _plain_scalar, _punctuation_scalar)

#: `[a-z][a-z0-9_-]*`: the grammar's key rule (§4.5), matching `_KEY_PATTERN`
#: in `serializer.py`. Built directly rather than filtered through
#: `key_is_representable`, so the strategy does not depend on the code P7
#: exercises.
valid_key = st.builds(
    operator.add,
    st.sampled_from('abcdefghijklmnopqrstuvwxyz'),
    st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789_-', max_size=6),
)
#: Text likely to sit on the key/not-a-key boundary: uppercase, digits-first,
#: punctuation-first, empty, non-ASCII letters (incl. a roman numeral, which
#: is categorized `Nl` and so is not excluded by `key_is_representable`'s
#: uppercase check), NBSP, BOM, colon.
_key_boundary_alphabet = st.sampled_from([*'abcAB19_-.: \t\xa0\ufeff\u200b#/', '\u540d', '\u216b', '\U0001f389'])
any_key = st.one_of(valid_key, st.text(alphabet=_key_boundary_alphabet, max_size=6), st.text(max_size=5))

data_valid: st.SearchStrategy[SymlData] = st.recursive(
    scalar,
    lambda children: st.lists(children, min_size=1, max_size=4)
    | st.dictionaries(valid_key, children, min_size=1, max_size=4),
    max_leaves=20,
)
data_any: st.SearchStrategy[object] = st.recursive(
    scalar,
    lambda children: st.lists(children, min_size=0, max_size=4)
    | st.dictionaries(any_key, children, min_size=0, max_size=4),
    max_leaves=20,
)

#: A single physical line built the same way `_seeded_line` is, reused by the
#: document strategies below (P3/P4/P5/P8).
_document_line = _seeded_line
_document_text = st.one_of(
    st.text(max_size=40),
    st.lists(_document_line, max_size=6).map('\n'.join),
    st.lists(st.tuples(st.sampled_from(['', ' ', '  ', '   ', '    ', '\t', '\xa0']), _document_line), max_size=6).map(
        lambda pairs: '\n'.join(indent + line for indent, line in pairs)
    ),
)


def _mutate_char(draw: st.DrawFn, op: str, line: str) -> str:
    """Apply one character-level edit (`ins`/`rep`/`del`) to `line` at a drawn position."""
    j = draw(st.integers(0, len(line)))
    if op == 'del':
        return line[:j] + line[j + 1 :]
    ch = draw(st.sampled_from([*_SEED_FRAGMENTS, *' -:#\t\r\n\xa0']) | st.characters())
    return line[:j] + ch + line[j:] if op == 'ins' else line[:j] + ch + line[j + 1 :]


def _mutate_indent(draw: st.DrawFn, line: str) -> str:
    """Add or strip up to 4 leading spaces from `line`."""
    delta = draw(st.integers(-4, 4))
    return (' ' * delta + line) if delta > 0 else line[min(-delta, len(line) - len(line.lstrip(' '))) :]


#: One in-place edit per single-line op name (everything but `swap`, `blank`,
#: `comment`, `dup`, `crlf`, `bom`, each of which changes the line count or
#: returns early and is handled directly in `mutated_document`).
_SINGLE_LINE_OPS = {
    'ins': lambda draw, line: _mutate_char(draw, 'ins', line),
    'rep': lambda draw, line: _mutate_char(draw, 'rep', line),
    'del': lambda draw, line: _mutate_char(draw, 'del', line),
    'indent': _mutate_indent,
    'trail': lambda draw, line: line + draw(st.sampled_from([' ', '  ', '\t'])),
}


def _apply_mutation(draw: st.DrawFn, op: str, lines: list[str], i: int) -> str | None:
    """Apply mutation `op` at line `i` of `lines` (mutated in place), or return early for `crlf`/`bom`."""
    if op in _SINGLE_LINE_OPS:
        lines[i] = _SINGLE_LINE_OPS[op](draw, lines[i])
    elif op == 'swap':
        k = draw(st.integers(0, len(lines) - 1))
        lines[i], lines[k] = lines[k], lines[i]
    elif op == 'blank':
        lines.insert(i, draw(st.sampled_from(['', '  ', '\t', ' \t '])))
    elif op == 'comment':
        lines.insert(i, draw(st.sampled_from(['', '  ', '    '])) + draw(st.sampled_from(['#', '//', '# c', '#####'])))
    elif op == 'dup':
        lines.insert(i, lines[i])
    elif op == 'crlf':
        return '\r\n'.join(lines)
    elif op == 'bom':
        return '\ufeff' + '\n'.join(lines)
    return None


@st.composite
def mutated_document(draw: st.DrawFn) -> str:
    """A `dumps`-derived (or arbitrary) text put through a handful of line-level mutations.

    Mirrors the probe's `mutated()`: starts from `dumps(data_valid)` (or a
    short arbitrary text when that value happens to be unrepresentable), then
    applies 1-4 of insert/delete/replace/swap/indent/blank/comment/trailing-
    whitespace/CRLF/BOM/duplicate-line, each bounded so the result stays well
    under the §13.4 nesting cliff (Contract 04 "Not checked: structural
    nesting").
    """
    x = draw(data_valid)
    try:
        text = serializer.dumps(x)
    except UnrepresentableValueError:
        text = draw(st.text(max_size=20))
    lines = text.split('\n')
    for _ in range(draw(st.integers(1, 4))):
        op = draw(
            st.sampled_from(['ins', 'del', 'rep', 'swap', 'indent', 'blank', 'comment', 'trail', 'crlf', 'bom', 'dup'])
        )
        if not lines:
            lines = ['']
        i = draw(st.integers(0, len(lines) - 1))
        result = _apply_mutation(draw, op, lines, i)
        if result is not None:
            return result
    return '\n'.join(lines)


def _safe_dumps(x: SymlData) -> str:
    try:
        return serializer.dumps(x)
    except UnrepresentableValueError:
        return ''


text_that_may_load = st.one_of(
    mutated_document(), st.lists(_document_line, max_size=6).map('\n'.join), data_valid.map(_safe_dumps)
)


def _strify(x: object) -> object:
    """Flatten an `as_source()` tree's `Source` leaves to plain `str` for comparison."""
    if isinstance(x, list):
        return [_strify(i) for i in x]
    if isinstance(x, dict):
        return {str(k): _strify(v) for k, v in x.items()}
    assert type(x) is not str, f'as_source leaked a plain str: {x!r}'
    return str(x)


def _contract_load(t: str) -> str:
    """Load `t` and classify the outcome as one of the two contract-allowed results."""
    try:
        syml.loads(t)
    except ParseError:
        return 'parseerror'
    return 'ok'


# ---------------------------------------------------------------------------
# P8's independent L1/L2/L3 predicates (Contract 04 §Load-only families)
#
# Reimplemented from the contract's own definitions, not by calling
# `serializer._later_line_marker_count`/`_lexes_as_structure`, so the P8
# oracle is not the code under test.
# ---------------------------------------------------------------------------

_CONTROL_CHAR = re.compile('[\x00-\x08\x0b-\x1f\x7f-\x9f]')
_MARKER_CHAIN = re.compile(r'(?:-[ \t]+)*-?')
_MAX_LATER_LINE_MARKERS = 32


def _is_l2(text: str) -> bool:
    """L2: the scalar contains a character rule D refuses (item 1)."""
    return bool(_CONTROL_CHAR.search(text))


def _is_l3(text: str) -> bool:
    """L3: a later line (index >= 1) whose leading marker chain holds > 32 markers (item 2)."""
    lines = text.split('\n')
    for line in lines[1:]:
        match = _MARKER_CHAIN.match(line.lstrip(' '))
        count = match.group().count('-') if match else 0
        if count > _MAX_LATER_LINE_MARKERS:
            return True
    return False


def _is_l1_mapping_value(text: str) -> bool:
    """L1: a multi-line mapping value whose first line is structure-shaped (item 2)."""
    lines = text.split('\n')
    return len(lines) > 1 and serializer._lexes_as_structure(lines[0])  # noqa: SLF001


def _scalars_in(x: SymlData, position: str) -> list[tuple[str, str]]:
    """Yield every (position, text) scalar in `x` ('root', 'mapping', or 'list')."""
    if isinstance(x, str):
        return [(position, x)]
    if isinstance(x, list):
        found = []
        for item in x:
            found.extend(_scalars_in(item, 'list'))
        return found
    found = []
    for value in x.values():
        found.extend(_scalars_in(value, 'mapping'))
    return found


def _load_only_family(position: str, text: str) -> str | None:
    """Classify a scalar as L1/L2/L3, or None if it isn't a load-only family."""
    if _is_l2(text):
        return 'L2'
    if position == 'mapping' and _is_l1_mapping_value(text):
        return 'L1'
    if _is_l3(text):
        return 'L3'
    return None


def _replace_load_only_scalars(x: SymlData) -> SymlData:
    """Return `x` with every L1/L2/L3 scalar replaced by `'x'` (P8's oracle clause)."""
    return _replace_load_only(x, 'root')


def _replace_load_only(x: SymlData, position: str) -> SymlData:
    if isinstance(x, str):
        return 'x' if _load_only_family(position, x) is not None else x
    if isinstance(x, list):
        return [_replace_load_only(item, 'list') for item in x]
    return {key: _replace_load_only(value, 'mapping') for key, value in x.items()}


def _check_load_first(t: str, *, record_events: bool = True) -> None:
    """P8's oracle: `loads(t)` must be one `dumps` can either write back or provably refuse."""
    try:
        x = syml.loads(t)
    except ParseError:
        return
    try:
        d = serializer.dumps(x)
    except UnrepresentableValueError:
        families = {
            family
            for position, text in _scalars_in(x, 'root')
            for family in [_load_only_family(position, text)]
            if family
        }
        assert families, f'dumps refused a value with no L1/L2/L3 scalar\nt={t!r}\nx={x!r}'
        if record_events:
            for family in families:
                event(family)
        x_prime = _replace_load_only_scalars(x)
        assert (
            syml.loads(serializer.dumps(x_prime)) == x_prime
        ), f'the rest of the document did not round-trip once L1/L2/L3 scalars were replaced\nt={t!r}\nx={x!r}'
        return
    assert syml.loads(d) == x, f'loads(dumps(x)) != x\nt={t!r}\nx={x!r}\nd={d!r}'
    assert not any(
        line.startswith(('#', '//')) for line in d.split('\n')
    ), f'a written line begins with a comment marker\nd={d!r}'


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


class TestP1DumpsThenLoadsRoundTripsOrRefuses:
    """P1: every value `dumps` accepts round-trips; every other value it refuses (SC-002)."""

    @given(data_valid)
    def test_it_should_round_trip_or_raise_unrepresentable(self, x: SymlData) -> None:
        try:
            d = serializer.dumps(x)
        except UnrepresentableValueError:
            event('unrepresentable')
            return
        back = syml.loads(d)
        assert back == x, f'round trip mismatch\nx={x!r}\nd={d!r}\nback={back!r}'
        assert serializer.dumps(back) == d, f'dumps not stable\nd={d!r}\nd2={serializer.dumps(back)!r}'
        event('roundtrip')


class TestP2DumpsTypeContract:
    """P2: any object either raises `TypeError`/`UnrepresentableValueError`, or round-trips."""

    @given(
        st.one_of(
            data_any,
            st.integers(),
            st.none(),
            st.tuples(st.text()),
            st.dictionaries(st.integers(), st.text(), min_size=1, max_size=2),
            st.lists(st.integers(), min_size=1, max_size=2),
        )
    )
    def test_it_should_raise_or_round_trip(self, x: object) -> None:
        try:
            d = serializer.dumps(x)  # type: ignore[arg-type]
        except (UnrepresentableValueError, TypeError):
            event('contract-exc')
            return
        back = syml.loads(d)
        assert back == x
        event('ok')


class TestP3LoadsNeverEscapesItsContract:
    """P3: `loads` on arbitrary or mutated text either succeeds or raises `ParseError`."""

    @given(_document_text)
    def test_it_should_load_or_raise_parse_error_on_random_text(self, t: str) -> None:
        event(_contract_load(t))

    @given(mutated_document())
    def test_it_should_load_or_raise_parse_error_on_mutated_text(self, t: str) -> None:
        event(_contract_load(t))


class TestP4AsDataAndAsSourceAgree:
    """P4: `loads`, `parse(...).as_data()`, and `strify(parse(...).as_source())` all agree."""

    @given(text_that_may_load)
    def test_it_should_agree_across_the_three_views(self, t: str) -> None:
        try:
            data = syml.loads(t)
        except ParseError:
            event('noload')
            return
        root = syml.parsers.parse(t)
        assert root.as_data() == data
        src = root.as_source()
        assert _strify(src) == data, f'as_source != as_data\nt={t!r}\nsrc={_strify(src)!r}\ndata={data!r}'
        event('checked')


class TestP5LoadsIsInvariantUnderTrivialTextVariants:
    """P5: a trailing LF, CRLF/CR normalization, and a leading BOM never change what `loads` returns."""

    @given(text_that_may_load)
    def test_it_should_agree_across_line_ending_and_bom_variants(self, t: str) -> None:
        if '\r' in t or t.startswith('\ufeff'):
            return
        try:
            data = syml.loads(t)
        except ParseError:
            event('noload')
            return
        for variant, name in (
            (t + '\n', 'trailing-LF'),
            (t.replace('\n', '\r\n'), 'CRLF'),
            (t.replace('\n', '\r'), 'CR'),
            ('\ufeff' + t, 'BOM'),
        ):
            v = syml.loads(variant)
            assert v == data, f'{name} changes data\nt={t!r}\nbase={data!r}\nvariant={v!r}'
        event('checked')


class TestP7KeyIsRepresentableAgreesWithTheGrammar:
    """P7: `key_is_representable` matches `[a-z][a-z0-9_-]*`, and an accepted key round-trips."""

    @given(any_key)
    def test_it_should_agree_with_the_key_regex(self, k: str) -> None:
        expected = re.fullmatch(r'[a-z][a-z0-9_-]*', k) is not None
        assert (
            serializer.key_is_representable(k) == expected
        ), f'key predicate disagrees for {k!r}: impl={serializer.key_is_representable(k)} spec={expected}'
        if expected:
            assert syml.loads(serializer.dumps({k: 'v'})) == {k: 'v'}
            event('representable')
        else:
            event('not-representable')


class TestP8LoadFirstEitherWritesBackOrProvablyRefuses:
    """P8: everything `loads` returns is either written back by `dumps`, or provably in L1/L2/L3.

    The refusal branch is an oracle (Contract 04 §Test obligations, red team
    outer iteration 7): `dumps` stops at the first refused scalar, so "`x`
    contains an L1/L2/L3 scalar" alone would pass a document that holds a
    wrongly-refused value elsewhere, hidden behind the first one. Requiring
    `x'` (every L1/L2/L3 scalar replaced by `'x'`) to still round-trip closes
    that gap: a fourth, unplanned load-only family fails this property.
    """

    @given(_document_text)
    def test_it_should_hold_for_random_documents(self, t: str) -> None:
        _check_load_first(t)

    @given(mutated_document())
    def test_it_should_hold_for_mutated_documents(self, t: str) -> None:
        _check_load_first(t)

    @pytest.mark.parametrize(
        't',
        [
            'k:\n  a\n  ' + '- ' * 40 + 'x',
            'k: note: the door\n  is locked',
            'notes: - milk\n  - eggs',
            '\x0bx',
            'k: a\x1cb',
        ],
    )
    def test_it_should_hold_for_the_contracts_named_load_only_rows(self, t: str) -> None:
        # Each of these rows is a documented load-only example (Contract 04's
        # "load-only" table): `loads` must succeed on it, or the row is no
        # longer testing what it claims to.
        syml.loads(t)
        _check_load_first(t, record_events=False)


class TestP6FixturesRoundTripOrAreProvablyLoadOnly:
    """P6: every fixture in `tests/fixtures/` satisfies the same P8 oracle."""

    @pytest.mark.parametrize('path', sorted(Path('tests/fixtures').glob('*.syml')), ids=lambda p: p.name)
    def test_it_should_hold_for_every_fixture(self, path: Path) -> None:
        _check_load_first(path.read_text(encoding='utf-8'), record_events=False)
