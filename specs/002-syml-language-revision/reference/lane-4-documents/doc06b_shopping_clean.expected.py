SOURCE = '''groceries:
  - milk
  - eggs: 12
  - Eggs: 12
  - produce:
    - apples
    - pears
  -
  - 
  - cheese
  - - brie
    - cheddar
'''
# `- produce:` then `    - apples` at col 4: the inline key `produce` is at col 4 (§6.2) so a child must
# be > 4. `- apples` at 4 == key level -> not child of produce; KeyValue(produce) section... sibling of
# produce in inline mapping requires KeyValue, ListItem rejected -> ERROR? Hedged prediction: ERROR.
SPEC = ('error', 'OutOfContextNodeError')
AUTHOR = {'groceries': ['milk', 'eggs: 12', 'Eggs: 12', {'produce': ['apples', 'pears']}, '', '', 'cheese',
                        ['brie', 'cheddar']]}
