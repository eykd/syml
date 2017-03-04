----
SYML
----

SYML (Simple YAML-like Markup Language) is a simple markup language with
similar structure to YAML, but without all the gewgaws and folderol.


Example
=======

Here's a simple SYML document::

  foo:
    - bar
    - baz
    - blah
      boo

  booleans?:
    - yes
    - no

And the resulting data structure::

  >>> import syml
  >>> syml.parse(document)
  OrderedDict([('foo', ['bar', 'baz', 'blah\nboo']),
               ('booleans?', ['yes', 'no'])])


All values in SYML are just plain ol' text. But let's face it, sometimes you
really do want YAML-like booleans::

  >>> import syml
  >>> syml.parse(document, booleans=True)
  OrderedDict([('foo', ['bar', 'baz', 'blah\nboo']),
               ('booleans?', [True, False])])
