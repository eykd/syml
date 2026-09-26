#!/usr/bin/env bash
# Prove the built sdist and wheel install and work, before anything uploads them.
#
# Usage:
#   scripts/smoke-install.sh            # build into a temp dir, then test
#   scripts/smoke-install.sh dist/      # test the artifacts already in dist/
#
# SMOKE_PYTHONS picks the interpreters (default: every version the
# classifiers claim). The release workflow sets it to one version to keep the
# tag-push job short.
#
# For each Python and each artifact, installs into a fresh venv and runs the
# embedded check from a temp dir, so no checkout's src/ can shadow the
# installed copy. Also checks the artifacts themselves: py.typed ships, no
# License :: classifier sits beside License-Expression (PyPI rejects that,
# PEP 639, and twine check does not), and the sdist carries no repo tooling.
set -euo pipefail

pythons=${SMOKE_PYTHONS:-"3.12 3.13 3.14"}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

if [[ $# -ge 1 ]]; then
  dist=$(cd "$1" && pwd)
else
  dist="$work/dist"
  uv build -q -o "$dist"
fi

shopt -s nullglob
wheels=("$dist"/*.whl)
sdists=("$dist"/*.tar.gz)
shopt -u nullglob
if [[ ${#wheels[@]} -ne 1 || ${#sdists[@]} -ne 1 ]]; then
  echo "FAIL: expected exactly one wheel and one sdist in $dist" >&2
  exit 1
fi
wheel=${wheels[0]}
sdist=${sdists[0]}
version=$(uv version --short)

fail() { echo "FAIL: $*" >&2; exit 1; }

# --- The artifacts themselves ---------------------------------------------
wheel_files=$(unzip -Z1 "$wheel")
grep -qx 'syml/py.typed' <<<"$wheel_files" || fail "wheel is missing syml/py.typed"
metadata=$(unzip -p "$wheel" "syml-$version.dist-info/METADATA") || fail "wheel has no syml-$version METADATA"
grep -q '^License-Expression: ' <<<"$metadata" || fail "METADATA has no License-Expression"
if grep -q '^Classifier: License ::' <<<"$metadata"; then
  fail "METADATA has a License :: classifier beside License-Expression; PyPI rejects this (PEP 639)"
fi
sdist_files=$(tar tzf "$sdist")
if grep -Eq '/(tests|specs|\.beads|\.claude|\.github)/' <<<"$sdist_files"; then
  fail "sdist ships repo tooling: $(grep -E '/(tests|specs|\.beads|\.claude|\.github)/' <<<"$sdist_files" | head -3)"
fi
grep -q '/src/syml/py.typed$' <<<"$sdist_files" || fail "sdist is missing src/syml/py.typed"
echo "ok   artifacts: py.typed shipped, no license classifier, sdist clean"

# --- The installed package ------------------------------------------------
cat >"$work/smoke.py" <<'PY'
import importlib.metadata
import io
import pathlib
import sys
import sysconfig

import syml
from syml import DuplicateKeyError, EncodingError, OutOfContextNodeError, ParseError, UnrepresentableValueError
from syml.basetypes import Source

expected_version = sys.argv[1]
site = pathlib.Path(sysconfig.get_paths()['purelib']).resolve()
package = pathlib.Path(syml.__file__).resolve().parent
assert package.is_relative_to(site), f'syml imported from {package}, not the venv at {site}'
assert importlib.metadata.version('syml') == expected_version, importlib.metadata.version('syml')
assert (package / 'py.typed').is_file(), 'installed package has no py.typed'

document = '\nfoo:\n  - bar\n  - baz\n  - blah\n    boo\n    baloon\n'
assert syml.loads(document) == {'foo': ['bar', 'baz', 'blah\nboo\nbaloon']}
assert syml.load(io.BytesIO(b'a: b\n')) == {'a': 'b'}
data = {'a': ['b', 'c\nd'], 'e': {'f': 'g'}}
assert syml.loads(syml.dumps(data)) == data
missing = [name for name in syml.__all__ if not hasattr(syml, name)]
assert not missing, f'__all__ names missing: {missing}'


def raised(exc, fn, *args):
    try:
        fn(*args)
    except exc as err:
        return err
    raise AssertionError(f'{exc.__name__} not raised')


err = raised(OutOfContextNodeError, syml.loads, 'a:\n  b: 1\n  c:2\n')
assert isinstance(err, ParseError) and 'needs a space after it' in str(err), err
assert 'first defined at line 1' in str(raised(DuplicateKeyError, syml.loads, 'k: 1\nk: 2\n'))
assert raised(UnrepresentableValueError, syml.dumps, {'a': ['x', {'Bad': 'v'}]}).path == ('a', 1)
raised(EncodingError, syml.load, io.BytesIO(b'a: \xff\n'))
assert Source.from_text('')
PY

for py in $pythons; do
  for artifact in "$wheel" "$sdist"; do
    kind=wheel
    [[ $artifact == "$sdist" ]] && kind=sdist
    venv="$work/venv-$py-$kind"
    uv venv -q --python "$py" "$venv"
    VIRTUAL_ENV="$venv" uv pip install -q "$artifact"
    (cd "$work" && "$venv/bin/python" smoke.py "$version") || fail "smoke check on Python $py, $kind"
    echo "ok   Python $py, $kind"
  done
done
echo "✅ smoke-install passed (syml $version)"
