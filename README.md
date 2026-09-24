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

booleans?:
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
 'booleans?': ['True', 'False', 'true', 'false', 'TRUE', 'FALSE']}
```


All leaf values in SYML are just plain ol' strings. No ints, floats, bools, or
nasty remote code execution bugs!


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
`-` on its own line, each line of the value indented beneath it). The output
format is otherwise an implementation choice, not part of the SYML
conformance requirements: two-space indentation, no blank lines, exactly one
trailing newline, and keys written in insertion order. `dumps` raises
`TypeError` for anything that isn't `str`, `list`, or `dict` (including a
non-`str` mapping key), and `UnrepresentableValueError` for a value with no
SYML encoding — a control character, a leading space or tab, a blank or
`#`-initial or structure-shaped line inside a multi-line value, a `- x` or
`key: v` shaped list item, or a mapping key with whitespace, a colon, or an
uppercase letter (see the specification's §11.2.1–§11.2.3).

`dump` writes through the file object's own codec and does not check it, so
always open the handle with `encoding='utf-8'` — SYML documents are UTF-8.

Upgrading from 0.6.2? See [CHANGELOG.md](CHANGELOG.md) for every user-visible
change.
