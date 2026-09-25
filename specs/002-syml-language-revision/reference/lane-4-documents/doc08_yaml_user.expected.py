SOURCE = '''name: "quoted"
nick: 'single'
tags: [a, b]
opts: {a: 1}
empty: null
flag: true
count: 123
nothing: ~
anchor: &base value
ref: *base
comment: value # trailing
people:
  - name: x
    age: 3
  - name: y
    age: 4
'''
SPEC = {'name': '"quoted"', 'nick': "'single'", 'tags': '[a, b]', 'opts': '{a: 1}', 'empty': 'null',
        'flag': 'true', 'count': '123', 'nothing': '~', 'anchor': '&base value', 'ref': '*base',
        'comment': 'value # trailing', 'people': [{'name': 'x', 'age': '3'}, {'name': 'y', 'age': '4'}]}
# A YAML user expects quotes stripped, comment stripped; everything else they accept as strings
AUTHOR = dict(SPEC, name='quoted', nick='single', comment='value')
