import sys, pathlib, runpy, json
sys.path.insert(0, '.')
import syml
R = pathlib.Path('/Users/eykd/code/py/syml')
# fixtures: compare with current (installed) syml output
import importlib
sys.path.insert(0, str(R / 'src'))
for f in sorted((R/'tests/fixtures').glob('*.syml')):
    t = f.read_text()
    if f.name == 'bar.syml':
        t = t.replace('  - when:\n    - Bar >= 2', '  - when:\n      - Bar >= 2')
    try: got = syml.loads(t)
    except Exception as e: got = f'{type(e).__name__}: {e}'
    print(f.name, 'loads ok' if not isinstance(got, str) else got)
    globals()[f.stem] = got
docs = R/'specs/002-syml-language-revision/reference/lane-4-documents'
for f in sorted(docs.glob('*.syml')):
    t = f.read_text(encoding='utf-8')
    ns = runpy.run_path(str(f.with_suffix('.expected.py')))
    if f.stem == 'doc01b_scene_taxi': t = t.replace('Given:', 'given:', 1)
    try: got = syml.loads(ns['SOURCE'] if f.stem != 'doc01b_scene_taxi' else ns['SOURCE'].replace('Given:', 'given:', 1))
    except Exception as e: got = ('error', type(e).__name__)
    au = ns['AUTHOR']
    print(f.stem, 'AUTHOR-MATCH' if got == au else 'DIFF', repr(got)[:300])
