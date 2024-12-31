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
