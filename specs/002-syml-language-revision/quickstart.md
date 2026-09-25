# Quickstart: Verifying the SYML Language Revision

**Feature**: `002-syml-language-revision` | **Plan**: [plan.md](./plan.md)

How to check, by hand and by suite, that the revision behaves as specified.
Run from the repository root.

## 1. Gates

```sh
uv sync --all-groups          # picks up hypothesis in the test group
just check                    # ruff + mypy + pytest (unit, incl. the round-trip property)
just acceptance               # pytest-bdd: US10–US13 plus the rewritten 001 suites
```

The 100% coverage gate runs in pre-commit and CI, not in `uv run pytest`.

## 2. Values are just text (US1)

```python
import syml

syml.loads('k:\n  Para one.\n\n  Para two.')
# {'k': 'Para one.\n\nPara two.'}

syml.loads('k:\n  some prose\n  - used as a dash\n  more')
# {'k': 'some prose\n- used as a dash\nmore'}

syml.loads('- Share is\n  //server/share')
# ['Share is\n//server/share']

syml.loads('# not a comment')
# '# not a comment'

syml.loads('env:\n  HOME: /h\n  PATH: /p')
# {'env': 'HOME: /h\nPATH: /p'}      (uppercase would-be keys are text)

syml.loads('  hello\nworld')
# '  hello\nworld'                   (root scalar keeps its indentation)

syml.loads('k:\n  - a\n  - b')
# {'k': ['a', 'b']}                  (a block's first line still decides structure)
```

## 3. Strict structure and honest errors (US2)

```python
syml.loads('k:\tv')                   # {'k': 'v'}      tab is separator whitespace
syml.loads('\xa0k: v')                # '\xa0k: v'      only U+0020 is indentation

try:
    syml.loads('k:\n- a', filename='f.syml')
except syml.OutOfContextNodeError as e:
    print(e)
# f.syml:2:0: Line 2, at column 0, does not fit any open block; open blocks are at column 0. Hint: a list under a key must be indented past the key's column.
# - a

try:
    syml.loads('\ufeffa: b\r\n\tc: d')
except syml.TabIndentationError as e:
    print(e.position)
# Pos(index=7, line=2, column=0)
```

## 4. The serializer writes what the parser reads (US3)

```python
syml.dumps({'k': 'Para one.\n\nPara two.'})
# 'k:\n  Para one.\n\n  Para two.\n'

syml.dumps(syml.parse('k: v').as_source())
# 'k: v\n'

syml.dumps('')
# ''

syml.dumps({'k': 'a\n \nb'})
# UnrepresentableValueError   (a whitespace-only line would read back empty)
```

## 5. Documents and release (US4)

```sh
uv run pytest tests/test_spec_examples.py --no-cov   # every Output/ERROR example + §4.1 grammar identity
git ls-remote --tags origin | grep 1.0.0             # after the release leaf
```

Read the README's "Coming from YAML" section and CHANGELOG's 1.0.0 entry
against sections 2–4 above: every behaviour shown here should be predictable
from them (SC-008).

## 6. The break-test ledger

```sh
br list --label break-test --status open --json | jq length   # 0 when the feature is done (SC-001)
```
