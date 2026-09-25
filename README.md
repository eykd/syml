SYML
----

![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/eykd/syml/ci.yaml)
![PyPI - Version](https://img.shields.io/pypi/v/syml)


SYML (Simple YAML-like Markup Language) is a simple markup language with
similar structure to YAML, but without all the gewgaws and folderol.


Example
=======

Here's a simple SYML document:

``` python

>>> document = """
foo:
  - bar
  - baz
  - blah
    boo
    baloon

booleans:
  - True
  - False
  - true
  - false
  - TRUE
  - FALSE
"""
```

And the resulting data structure::

``` python
>>> import syml
>>> syml.loads(document)
{'foo': ['bar', 'baz', 'blah\nboo\nbaloon'],
 'booleans': ['True', 'False', 'true', 'false', 'TRUE', 'FALSE']}
```


All leaf values in SYML are just plain ol' strings. No ints, floats, bools, or
nasty remote code execution bugs!


Coming from YAML
=================

SYML looks like YAML, but several YAML features are deliberately absent.
Skimming a YAML file into SYML? Watch for these, in order:

1. **Comments only at column 0.** A line that starts with `#` or `//`, with
   no indentation, is a comment, anywhere in the file. An indented `# note`
   is text: as the first line of a block it makes that block one string,
   with no error, and after a block's first entry it raises. A trailing
   comment is text too (`port: 80 # default` keeps `# default`), and after
   a key it takes in the block under it (`server: # prod` makes the block
   under it part of `server`'s string).
2. **No block-scalar indicators.** `|` and `>` are literal characters, not
   YAML's literal/folded block markers; indent the lines under the key
   instead.
3. **No document markers.** `---` and `...` are text, not YAML's document
   separators (a document starting with one is a single string).
4. **No quoting.** `"x"` is the three-character string `"x"`, quotation
   marks included.
5. **Bare scalars are plain strings.** `null`, `true`, `123`, `~`,
   `[a, b]`, and `{a: 1}`, written inline, are all just their literal text.
6. **Keys match `[a-z][a-z0-9_-]*`.** `Name:`, `firstName:`, and `URL:` are
   text, not keys: a block of them (`env:\n  HOME: /h`) is one text value,
   and so is a whole file whose first line is one
   (`Name: app\nport: 80` is a string), and so is a list item whose first
   key is one (`- containerPort: 80\n  protocol: TCP` is one string). A
   bad key after a good one raises with a hint.
7. **`- key:` sets a sibling column.** `- server:\n  host: x` is two
   siblings (`[{'server': '', 'host': 'x'}]`); `- server:\n    host: x`
   nests (`[{'server': {'host': 'x'}}]`). Use a space after `-`: a tab
   there counts as one column too, but is easy to misalign visually.
8. **A blank line inside a value is a paragraph break.** `k:\n  a\n\n  b`
   is `{'k': 'a\n\nb'}`, not `{'k': 'a\nb'}`.


`Source`
========

`syml.parse` returns a tree whose leaves carry `Source` objects instead of
plain `str` (see [`syml.basetypes.Source`](src/syml/basetypes.py)). Three
facts distinguish it from `str`:

- **`Source` is not a `str`.** It compares equal to a `str` with the same
  text and hashes the same way, so it works as a dict key or in a set
  alongside plain strings, but `isinstance(source, str)` is `False`.
- **An empty `Source` is truthy.** `bool(Source(text=''))` is `True` even
  though `bool('')` is `False`, and `Source` has no `__len__`, so `len()`
  raises `TypeError` rather than returning `0`.
- **A multi-line `Source.text` is the dedented value.** It is exactly the
  string `as_data()` would return for the same node — indentation past the
  baseline preserved, indentation up to the baseline stripped — not the
  raw source slice.


Serializing
===========

`syml.dumps` and `syml.dump` serialize plain `str`/`list`/`dict` data back to
SYML text, such that `loads(dumps(x)) == x`:

``` python
>>> import syml
>>> syml.dumps({'foo': ['bar', 'baz']})
"foo:\n  - bar\n  - baz\n"
```

``` python
>>> with open('out.syml', 'w', encoding='utf-8') as f:
...     syml.dump({'foo': ['bar', 'baz']}, f)
```

SYML has no quoted strings: every value is the literal text on the page, so
a `'` or `"` is ordinary content and `"hello"` round-trips with its quotation
marks. A string containing a newline is written in block form (the key or
`-` on its own line, each line of the value indented beneath it), and any
root scalar is written in block form too, keeping its own leading spaces
literally (`dumps('  hello')` is `'  hello\n'`); a blank
line inside the value is written back as an empty line (a paragraph break),
not dropped. The output format is otherwise an implementation choice, not
part of the SYML conformance requirements: two-space indentation, exactly
one trailing newline, and keys written in insertion order. `dumps` accepts
plain `str`/`list`/`dict` data, and also accepts `syml.basetypes.Source`
wherever a `str` key or scalar is expected (it is written by its text).
It raises `TypeError` for anything else (including a mapping key that is
neither a `str` nor a `Source`), and `UnrepresentableValueError` for a
value with no SYML encoding: a control character other than LF/TAB
anywhere; a first line that would lex as structure (at a list position, at
a mapping position for a multi-line value, or at the root regardless of
length), plus any later line whose leading `- ` marker chain holds more
than 32 markers; a value's first line, inline or block, beginning with a
space (mapping or list position only — a root scalar's leading spaces are
literal content, see above); any line whose leading whitespace contains a
tab; a non-empty, whitespace-only line; a multi-line value whose first or
last line is empty; a mapping key that does not match `[a-z][a-z0-9_-]*`;
an empty list or empty mapping at any depth; and a root scalar with any
line beginning with `#` or `//` (see the specification's §11.2.1–§11.2.3).

`dump` writes through the file object's own codec and does not check it, so
always open the handle with `encoding='utf-8'` — SYML documents are UTF-8.

Upgrading from 0.6.2? See [CHANGELOG.md](CHANGELOG.md) for every user-visible
change.
