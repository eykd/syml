SOURCE = 'name: widget\r\ntitle:\tHello\r\nport: 80\r\n'
# Spec §7.5: `title:\tHello` is text at a Mapping's level -> error.
SPEC = ('error', 'OutOfContextNodeError')
AUTHOR = {'name': 'widget', 'title': 'Hello', 'port': '80'}
