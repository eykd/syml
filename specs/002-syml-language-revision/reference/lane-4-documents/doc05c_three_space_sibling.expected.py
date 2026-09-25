SOURCE = '''parent:
  child1: a
  child2: b
   child3: c
'''
# §4.2/§8.1: child3 at 3 spaces -> error. (Note: child2 holds inline value, so it can't be a parent.)
SPEC = ('error', 'OutOfContextNodeError')
AUTHOR = {'parent': {'child1': 'a', 'child2': 'b', 'child3': 'c'}}
