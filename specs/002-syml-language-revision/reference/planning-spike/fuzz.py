import sys; sys.path.insert(0, '.')
import syml, syml.serializer as S
from hypothesis import given, settings, strategies as st, HealthCheck
ALPHA = st.sampled_from(list('ab -:#/\t\xa0﻿Kx') + ['\n', '\n\n', '  ', 'k: ', '- ', 'k:'])
scal = st.lists(ALPHA, max_size=10).map(''.join)
keys = st.from_regex(r'[a-z][a-z0-9_-]{0,3}', fullmatch=True)
data = st.recursive(scal, lambda c: st.lists(c, min_size=1, max_size=3) | st.dictionaries(keys, c, min_size=1, max_size=3), max_leaves=8)
stats = {'ok':0,'unrep':0}
@settings(max_examples=int(sys.argv[1]) if len(sys.argv)>1 else 3000, deadline=None, suppress_health_check=list(HealthCheck), database=None)
@given(data)
def rt(x):
    try:
        d = syml.dumps(x)
    except syml.UnrepresentableValueError:
        stats['unrep'] += 1; return
    back = syml.loads(d)
    assert back == x, (x, d, back)
    stats['ok'] += 1
rt(); print('roundtrip', stats)
# minimality probe: for refused scalars, try every layout at each position
def spellings(v, pos):
    ls = v.split('\n')
    if pos == 'root':
        yield v
        return
    m = 'k:' if pos == 'mapping' else '-'
    yield f'{m} {v}' if '\n' not in v else None
    for ind in (2, 3, 4):
        yield m + '\n' + '\n'.join((' ' * ind + l) if l else '' for l in ls)
    yield f'{m} {ls[0]}\n' + '\n'.join(('  ' + l) if l else '' for l in ls[1:]) if len(ls) > 1 else None
def wrap(v, pos): return v if pos == 'root' else ({'k': v} if pos == 'mapping' else [v])
found = []
@settings(max_examples=int(sys.argv[1]) if len(sys.argv)>1 else 3000, deadline=None, suppress_health_check=list(HealthCheck), database=None)
@given(scal, st.sampled_from(['root', 'mapping', 'list']))
def minimal(v, pos):
    try:
        syml.dumps(wrap(v, pos)); return
    except syml.UnrepresentableValueError:
        pass
    for sp in spellings(v, pos):
        if sp is None: continue
        try:
            if syml.loads(sp) == wrap(v, pos):
                found.append((v, pos, sp)); return
        except Exception:
            pass
minimal(); print('refused-but-spellable', len(found), found[:8])
print('families', {(pos, S._lexes_as_structure(v.split('\n')[0]), sp.split('\n')[0].startswith(('k: ', '- '))) for v, pos, sp in found})
