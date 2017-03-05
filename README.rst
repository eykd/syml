----
SYML
----

SYML (Simple YAML-like Markup Language) is a simple markup language with
similar structure to YAML, but without all the gewgaws and folderol.

.. image:: https://travis-ci.org/eykd/syml.svg?branch=master
    :target: https://travis-ci.org/eykd/syml

.. image:: https://coveralls.io/repos/github/eykd/syml/badge.svg?branch=master
    :target: https://coveralls.io/github/eykd/syml?branch=master


Example
=======

Here's a simple SYML document::

  >>> document = """
  foo:
    - bar
    - baz
    - blah
      boo

  booleans?:
    - yes
    - no
    - true
    - false
    - on
    - off
  """

And the resulting data structure::

  >>> import syml
  >>> syml.loads(document)
  OrderedDict([('foo', ['bar', 'baz', 'blah\nboo']),
               ('booleans?', ['yes', 'no', 'true', 'false', 'on', 'off'])])


All values in SYML are just plain ol' text. But let's face it, sometimes you
really do want YAML-like booleans::

  >>> import syml
  >>> syml.loads(document, booleans=True)
  OrderedDict([('foo', ['bar', 'baz', 'blah\nboo']),
               ('booleans?', [True, False, True, False, True, False])])
