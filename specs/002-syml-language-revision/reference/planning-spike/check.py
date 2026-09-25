import sys; sys.path.insert(0, '.')
import syml
E = object()
cases = [
 ('k:\n  Para one.\n\n  Para two.', {"k": "Para one.\n\nPara two."}),
 ('Para one.\n\nPara two.', "Para one.\n\nPara two."),
 ('k:\n  some prose\n  - used as a dash\n  more', {"k": "some prose\n- used as a dash\nmore"}),
 ('- Share is\n  //server/share', ["Share is\n//server/share"]),
 ('- tag line\n  #winning', ["tag line\n#winning"]),
 ('port: 8080 # default', {"port": "8080 # default"}),
 ('- [ask: why?]', ["[ask: why?]"]), ('- "listen: I know."', ['"listen: I know."']), ('- 3: 1 odds', ["3: 1 odds"]),
 ('"so: you came back."', '"so: you came back."'),
 ('env:\n  HOME: /h\n  PATH: /p', {"env": "HOME: /h\nPATH: /p"}),
 ('name: a\nfirstName: b\nage: 3', 'OutOfContextNodeError'),
 ('Given:\n  a: 1', "Given:\n  a: 1"),
 ('  hello', '  hello'), ('  hello\nworld', '  hello\nworld'), ('  hello\n    world', '  hello\n    world'),
 ('k:\n  a\n\n\n  b\n\n', {"k": "a\n\n\nb"}),
 ('k:\n\n  a', {"k": "a"}),
 ('k:\n  a\n\nb: 2', {"k": "a", "b": "2"}),
 ('# one\n// two\n  # three', "# one\n// two\n  # three"), ('# c', '# c'),
 ('a:\n  b: 1\n  # note', 'OutOfContextNodeError'),
 ('k: first\n  - second\n  key: third', {"k": "first\n- second\nkey: third"}),
 ('k:\n  - a\n  - b', {"k": ["a", "b"]}), ('k:\n  x: 1\n  y: 2', {"k": {"x": "1", "y": "2"}}),
 ('k: a\n    b\n  c', 'OutOfContextNodeError'),
 # US2
 ('k:\n- a\n- b', 'OutOfContextNodeError'), ('a:\n- x\n- y\nb: z', 'OutOfContextNodeError'), ('- key:\n  - x', 'OutOfContextNodeError'),
 ('- server:\n  host: x', [{"server": "", "host": "x"}]),
 ('k:\tv', {"k": "v"}), ('a:\t\n  b: 1', {"a": {"b": "1"}}), ('- a\n-\tx', ["a", "x"]),
 ('a:\n\tb', 'TabIndentationError'),
 ('\xa0k: v', "\xa0k: v"), ('k:\n  a\n\xa0\n  b', 'OutOfContextNodeError'),
 ('\x0bx', "\x0bx"), ('\x0c', "\x0c"), ('\u2028- x', "\u2028- x"),
 ('k:\n  a: 1\n   b: 2', 'OutOfContextNodeError'),
 ('a: 1\n  - x', 'OutOfContextNodeError'),
 ('a: 1\r\n\tb: 2', 'TabIndentationError'), ('\ufeff\tk: v', 'TabIndentationError'),
 ('key: v\n\xa0\tx', 'OutOfContextNodeError'),
 # edge cases
 ('hello\nk: v', "hello\nk: v"), ('---\nk: v', "---\nk: v"), ('k: v\nhello', 'OutOfContextNodeError'),
 ('\n  \n\t\n', ''), ('\xa0', '\xa0'),
 ('- key:\n    - x', [{"key": ["x"]}]),
 ('k: first\n\n  second', {"k": "first\n\nsecond"}),
 ('- a\n\n- b', ['a', 'b']),
 ('k:\n  a\n      \n  b', {'k': 'a\n\nb'}),
 ('k: \tv', {'k': 'v'}), ('key: \t', {'key': ''}),
 ('- - x', [['x']]), ('- name: Alice\n  role: admin', [{'name': 'Alice', 'role': 'admin'}]),
 ('- name: Alice\n    more\n  role: admin', [{'name': 'Alice\nmore', 'role': 'admin'}]),
 ('note: hello\n  more: text', {'note': 'hello\nmore: text'}),
 ('a:\n  b: 1\n  plain', 'OutOfContextNodeError'),
 ('- item1\n- item2\nkey: value', 'OutOfContextNodeError'),
 ('parent:\n  child1: value\n   child2: value', 'OutOfContextNodeError'),
 ('-\n  block item', ['block item']),
 ('empty:\nnext: value', {'empty': '', 'next': 'value'}),
 ('k:\n  first\n    indented\n  back', {'k': 'first\n  indented\nback'}),
 ('hello\n  world\nagain', 'hello\n  world\nagain'),
 ('k:\n  a\n   \n  b', {'k': 'a\n\nb'}),
 ('', ''), ('\n', ''), ('k: v\n', {'k': 'v'}),
]
bad = 0
for text, exp in cases:
    try:
        got = syml.loads(text)
    except Exception as e:
        got = type(e).__name__
    if got != exp:
        bad += 1
        print('MISMATCH', repr(text), 'got', repr(got), 'exp', repr(exp))
print('done', len(cases), 'bad', bad)
