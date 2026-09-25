SOURCE = '''---
key: value
...
'''
# `---` is text (no ws after -), root TextLeaf; `key: value` at level 0 can't join -> error
SPEC = ('error', 'OutOfContextNodeError')
AUTHOR = {'key': 'value'}
