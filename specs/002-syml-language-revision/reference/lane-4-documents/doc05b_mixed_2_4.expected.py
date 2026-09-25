SOURCE = '''a:
  b: 1
    
c:
    d: 2
    e:
      - x
      - y
'''
# per-block indentation widths differ but each block is self-consistent; whitespace-only line is blank
SPEC = {'a': {'b': '1'}, 'c': {'d': '2', 'e': ['x', 'y']}}
AUTHOR = SPEC
