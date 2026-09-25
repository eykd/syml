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
SPEC = {'groceries': ['milk', {'eggs': '12'}, 'Eggs: 12', {'produce': ['apples', 'pears']}, '', '', 'cheese',
                      ['brie', 'cheddar']]}
AUTHOR = {'groceries': ['milk', 'eggs: 12', 'Eggs: 12', {'produce': ['apples', 'pears']}, '', '', 'cheese',
                        ['brie', 'cheddar']]}
