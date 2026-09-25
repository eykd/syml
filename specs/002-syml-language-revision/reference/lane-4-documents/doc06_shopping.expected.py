SOURCE = '''groceries:
  - milk
  - eggs: 12
  - Eggs: 12
  - bread
    - rye
    - sourdough
  - produce:
    - apples
    - pears
  -
  - 
  - cheese
  - - brie
    - cheddar
'''
# - eggs: 12 -> inline mapping {'eggs': '12'} (§7.2); - Eggs: 12 -> text (§4.1 uppercase)
# - bread + nested `- rye` -> ListItem holding inline value is closed (§9.3) -> ERROR expected here.
SPEC = ('error', 'OutOfContextNodeError')
AUTHOR = {'groceries': ['milk', 'eggs: 12', 'Eggs: 12', 'bread', ['rye', 'sourdough'], {'produce': ['apples', 'pears']},
                        '', '', 'cheese', ['brie', 'cheddar']]}
