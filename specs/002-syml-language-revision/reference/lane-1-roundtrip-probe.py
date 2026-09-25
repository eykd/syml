"""Lane 1: property-based round-trip fuzzing of syml 1.0.0.

Run: cd /Users/eykd/code/py/syml && uv run --with hypothesis python <this> [prop ...]
Each property records failures (shrunk) into failures/<prop>.txt and continues.
"""

from __future__ import annotations

import enum
import json
import signal
import sys
import traceback
import unicodedata
from contextlib import contextmanager
from pathlib import Path

import parsimonious
from hypothesis import HealthCheck, assume, given, note, settings, strategies as st
from hypothesis.errors import Found  # noqa: F401  (hypothesis internal, unused)

import syml
from syml.serializer import key_is_representable

OUT = Path(__file__).parent
N = int(__import__('os').environ.get('N', '2000'))
FILTER_KNOWN = __import__('os').environ.get('FILTER_KNOWN', '1') == '1'


class Timeout(Exception):
    pass


@contextmanager
def alarm(sec: int = 10):
    def h(*_):
        raise Timeout
    old = signal.signal(signal.SIGALRM, h)
    signal.alarm(sec)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


# Unicode White_Space per spec §4.5
WHITE_SPACE = set('\t\n\x0b\x0c\r \x85\xa0     　') | {chr(c) for c in range(0x2000, 0x200B)}
# chars Python's \s matches that are NOT U+0020/U+0009 (the known family, finding F1)
PY_SPACE_EXTRA = {chr(c) for c in range(0x110000) if chr(c).isspace()} - {' ', '\t', '\n'}

SEED_STARTS = [
    '﻿', '\xa0', ' ', ' ', '\x85', '　', '\x0c', '\x0b', '\x1c', '\x1d', '\x1e', '\x1f',
    '́', '\U0001F600', '\t', ' ', '  ', '-', '- ', '- -', '#', '//', 'key:', 'key: ', 'Key: ', ':', 'k:v',
    '- k: ', '-\t', ' ', ' ', '​', '\x00', '\x7f', '\x9f', '\ud800', "'", '"',
]
BODY_ALPHA = st.characters(codec=None, exclude_characters='\n') | st.sampled_from(list('ab -:#/\t') + [c for c in SEED_STARTS if len(c) == 1])
body = st.text(alphabet=BODY_ALPHA, max_size=8)
line = st.tuples(st.sampled_from(SEED_STARTS + [''] * 8), body).map(''.join)
seeded_scalar = st.lists(line, min_size=0, max_size=4).map('\n'.join)
plain_scalar = st.text(max_size=12)
simple_scalar = st.text(alphabet='abc XYZ-:#/\n\t\'"', max_size=12)
scalar_str = st.one_of(seeded_scalar, plain_scalar, simple_scalar)


class S(str):
    pass


class E(str, enum.Enum):
    A = 'alpha'
    B = 'x\ny'
    C = '- x'


scalar = st.one_of(scalar_str, scalar_str.map(S), st.sampled_from(list(E)))

KEY_ALPHA = st.characters(exclude_categories=('Lu', 'Lt', 'Cs'), exclude_characters=''.join(WHITE_SPACE) + ':') | st.sampled_from(list('abc_.-/#﻿0') + ['名', 'Ⅻ', '\U0001F389'])
valid_key = st.text(alphabet=KEY_ALPHA, min_size=1, max_size=6).filter(key_is_representable)
any_key = st.one_of(valid_key, st.text(max_size=5))

data_valid = st.recursive(
    scalar,
    lambda c: st.lists(c, min_size=1, max_size=4) | st.dictionaries(valid_key, c, min_size=1, max_size=4),
    max_leaves=20,
)
data_any = st.recursive(
    scalar,
    lambda c: st.lists(c, min_size=0, max_size=4) | st.dictionaries(any_key, c, min_size=0, max_size=4),
    max_leaves=20,
)


def strings_in(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, list):
        for i in x:
            yield from strings_in(i)
    elif isinstance(x, dict):
        for k, v in x.items():
            yield k
            yield from strings_in(v)


def known_family(x) -> bool:
    """True if some string value has a Python-\\s (non ' '/'\\t') char at a line start or a line of only such chars.

    That is finding F1's mechanism; filtered out so other bugs surface.
    """
    for s in strings_in(x):
        for ln in s.split('\n'):
            rest = ln.lstrip(' ')
            if rest[:1] in PY_SPACE_EXTRA:
                return True
    return False


def plainify(x):
    """Convert str subclasses/enums to plain str/list/dict for comparison."""
    if isinstance(x, str):
        return str.__str__(x)
    if isinstance(x, list):
        return [plainify(i) for i in x]
    return {str.__str__(k): plainify(v) for k, v in x.items()}


FAILS: dict[str, list[str]] = {}


def record(prop: str, msg: str) -> None:
    FAILS.setdefault(prop, []).append(msg)


def cfg(n=N):
    return settings(max_examples=n, deadline=None, suppress_health_check=list(HealthCheck), database=None, report_multiple_bugs=True)


COUNTS: dict[str, dict[str, int]] = {}


def bump(prop, k):
    COUNTS.setdefault(prop, {}).setdefault(k, 0)
    COUNTS[prop][k] += 1


# ---------------- P1 / P2 ----------------
@cfg()
@given(data_valid)
def p1(x):
    if FILTER_KNOWN:
        assume(not known_family(x))
    with alarm():
        try:
            d = syml.dumps(x)
        except syml.UnrepresentableValueError:
            bump('P1', 'unrep')
            return
    bump('P1', 'dumped')
    with alarm():
        try:
            back = syml.loads(d)
        except Exception as e:  # noqa: BLE001
            raise AssertionError(f'loads(dumps(x)) raised {type(e).__name__}: {e}\nx={x!r}\nd={d!r}') from None
    assert back == plainify(x), f'round trip mismatch\nx={x!r}\nd={d!r}\nback={back!r}'
    assert syml.dumps(back) == d, f'dumps not stable\nd={d!r}\nd2={syml.dumps(back)!r}'
    bump('P1', 'roundtrip-ok')


@cfg()
@given(st.one_of(data_any, st.integers(), st.none(), st.tuples(st.text()), st.dictionaries(st.integers(), st.text(), min_size=1, max_size=2), st.lists(st.integers(), min_size=1, max_size=2)))
def p2(x):
    with alarm():
        try:
            syml.dumps(x)
            bump('P2', 'ok')
        except (syml.UnrepresentableValueError, TypeError):
            bump('P2', 'contract-exc')
        except RecursionError:
            bump('P2', 'recursion')


# ---------------- P3 ----------------
def contract_loads(t):
    try:
        with alarm():
            syml.loads(t)
        return 'ok'
    except syml.ParseError:
        return 'parseerror'
    except RecursionError:
        return 'recursion'
    except Timeout:
        raise AssertionError(f'timeout loads({t!r})') from None
    except Exception as e:  # noqa: BLE001
        raise AssertionError(f'out-of-contract {type(e).__name__}: {e}\ntext={t!r}') from None


@cfg()
@given(st.one_of(st.text(max_size=40), st.lists(line, max_size=6).map('\n'.join), st.lists(st.tuples(st.sampled_from(['', ' ', '  ', '   ', '    ', '\t', '\xa0']), line), max_size=6).map(lambda ls: '\n'.join(a + b for a, b in ls))))
def p3_random(t):
    bump('P3r', contract_loads(t))


@st.composite
def mutated(draw):
    x = draw(data_valid)
    try:
        d = syml.dumps(x)
    except syml.UnrepresentableValueError:
        d = draw(st.text(max_size=20))
    lines = d.split('\n')
    for _ in range(draw(st.integers(1, 4))):
        op = draw(st.sampled_from(['ins', 'del', 'rep', 'swap', 'indent', 'blank', 'comment', 'trail', 'crlf', 'bom', 'dup']))
        if not lines:
            lines = ['']
        i = draw(st.integers(0, len(lines) - 1))
        ln = lines[i]
        if op in ('ins', 'rep', 'del'):
            j = draw(st.integers(0, len(ln)))
            ch = draw(st.sampled_from(SEED_STARTS + list(' -:#\t\r\n\xa0')) | st.characters())
            if op == 'ins':
                ln = ln[:j] + ch + ln[j:]
            elif op == 'rep':
                ln = ln[:j] + ch + ln[j + 1:]
            else:
                ln = ln[:j] + ln[j + 1:]
            lines[i] = ln
        elif op == 'swap':
            k = draw(st.integers(0, len(lines) - 1))
            lines[i], lines[k] = lines[k], lines[i]
        elif op == 'indent':
            delta = draw(st.integers(-4, 4))
            lines[i] = (' ' * delta + ln) if delta > 0 else ln[min(-delta, len(ln) - len(ln.lstrip(' '))):]
        elif op == 'blank':
            lines.insert(i, draw(st.sampled_from(['', '  ', '\t', ' \t '])))
        elif op == 'comment':
            lines.insert(i, draw(st.sampled_from(['', '  ', '    '])) + draw(st.sampled_from(['#', '//', '# c', '#####'])))
        elif op == 'trail':
            lines[i] = ln + draw(st.sampled_from([' ', '  ', '\t']))
        elif op == 'dup':
            lines.insert(i, ln)
        elif op == 'crlf':
            return '\r\n'.join(lines)
        elif op == 'bom':
            return '﻿' + '\n'.join(lines)
    return '\n'.join(lines)


@cfg()
@given(mutated())
def p3_mut(t):
    bump('P3m', contract_loads(t))


# ---------------- P4 / P5 ----------------
def strify(x):
    if isinstance(x, list):
        return [strify(i) for i in x]
    if isinstance(x, dict):
        return {str(k): strify(v) for k, v in x.items()}
    assert type(x) is not str, f'as_source leaked a plain str: {x!r}'
    return str(x)


text_that_may_load = st.one_of(mutated(), st.lists(line, max_size=6).map('\n'.join), data_valid.map(lambda x: _safe_dumps(x)))


def _safe_dumps(x):
    try:
        return syml.dumps(x)
    except syml.UnrepresentableValueError:
        return ''


@cfg()
@given(text_that_may_load)
def p4(t):
    try:
        with alarm():
            data = syml.loads(t)
    except (syml.ParseError, RecursionError):
        bump('P4', 'noload')
        return
    root = syml.parse(t)
    assert root.as_data() == data
    src = root.as_source()
    assert strify(src) == data, f'as_source != as_data\nt={t!r}\nsrc={strify(src)!r}\ndata={data!r}'
    bump('P4', 'checked')


@cfg()
@given(text_that_may_load)
def p5(t):
    assume('\r' not in t and not t.startswith('﻿'))
    try:
        with alarm():
            data = syml.loads(t)
    except (syml.ParseError, RecursionError):
        bump('P5', 'noload')
        return
    for variant, name in ((t + '\n', 'trailing-LF'), (t.replace('\n', '\r\n'), 'CRLF'), (t.replace('\n', '\r'), 'CR'), ('﻿' + t, 'BOM')):
        try:
            v = syml.loads(variant)
        except Exception as e:  # noqa: BLE001
            raise AssertionError(f'{name}: loads raised {type(e).__name__} but base loaded\nt={t!r}') from None
        assert v == data, f'{name} changes data\nt={t!r}\nbase={data!r}\nvariant={v!r}'
    bump('P5', 'checked')


# ---------------- P7: key predicate vs spec ----------------
def spec_key_ok(k: str) -> bool:
    if not k or k.startswith(('#', '//')):
        return False
    for ch in k:
        o = ord(ch)
        if ch in WHITE_SPACE or ch == ':' or o <= 0x1F or 0x7F <= o <= 0x9F:
            return False
        if unicodedata.category(ch) in ('Lu', 'Lt'):
            return False
    return True


@cfg(5000)
@given(st.one_of(st.text(max_size=6), st.text(alphabet=st.sampled_from(sorted(WHITE_SPACE | PY_SPACE_EXTRA) + list('ab:#/Aǅ﻿​')), max_size=4)))
def p7(k):
    assert key_is_representable(k) == spec_key_ok(k), f'key predicate disagrees for {k!r}: impl={key_is_representable(k)} spec={spec_key_ok(k)}'
    if spec_key_ok(k):
        # and round-trips
        assert syml.loads(syml.dumps({k: 'v'})) == {k: 'v'}
    bump('P7', 'checked')


PROPS = {'p1': p1, 'p2': p2, 'p3r': p3_random, 'p3m': p3_mut, 'p4': p4, 'p5': p5, 'p7': p7}


def p6():
    res = []
    for f in sorted(Path('tests/fixtures').glob('*.syml')):
        data = syml.loads(f.read_text(encoding='utf-8'))
        try:
            d = syml.dumps(data)
        except syml.UnrepresentableValueError as e:
            res.append(f'{f.name}: dumps unrepresentable: {e}')
            continue
        back = syml.loads(d)
        res.append(f'{f.name}: {"OK" if back == data and syml.dumps(back) == d else "MISMATCH"}')
    return res


if __name__ == '__main__':
    sys.setrecursionlimit(3000)
    which = sys.argv[1:] or list(PROPS) + ['p6']
    for name in which:
        if name == 'p6':
            print('P6', p6(), flush=True)
            continue
        try:
            PROPS[name]()
            print(name, 'PASS', COUNTS, flush=True)
        except BaseException as e:  # noqa: BLE001
            msg = ''.join(traceback.format_exception_only(type(e), e))
            print(name, 'FAIL', COUNTS, '\n', msg[:4000], flush=True)
