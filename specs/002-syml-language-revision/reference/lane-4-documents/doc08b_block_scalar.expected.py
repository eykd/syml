SOURCE = '''poem: |
  roses are red
  violets are blue
folded: >
  one
  two
'''
SPEC = {'poem': '|\nroses are red\nviolets are blue', 'folded': '>\none\ntwo'}
AUTHOR = {'poem': 'roses are red\nviolets are blue\n', 'folded': 'one two\n'}
