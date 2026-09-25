SOURCE = '''title: On Gardens
body:
  Gardens take time. Nobody tells you this: they take years.

  A second paragraph, after a blank line.
      "An indented quote," she said.
  Things you need:
  1. patience
  2. a spade
  - compost
  - more compost
'''
# Spec: blank line dropped (§5.1 r5); indented quote keeps 4 extra spaces (§5.3); `1. patience` is text;
# `- compost` at level 2 is a ListItem at a continuation position -> body's KeyValue holds a TextLeaf
# and TextLeaf cannot take a ListItem -> OutOfContextNodeError.
SPEC = ('error', 'OutOfContextNodeError')
AUTHOR = {'title': 'On Gardens', 'body': 'Gardens take time. Nobody tells you this: they take years.\n\n'
          'A second paragraph, after a blank line.\n    "An indented quote," she said.\nThings you need:\n'
          '1. patience\n2. a spade\n- compost\n- more compost'}
