SOURCE = '''items:
- a
- b
other: c
'''
# YAML's very common "list at same indent as parent key" style. §4.2 r5: child must be deeper ->
# `- a` at level 0 while root holds a Mapping -> error.
SPEC = ('error', 'OutOfContextNodeError')
AUTHOR = {'items': ['a', 'b'], 'other': 'c'}
