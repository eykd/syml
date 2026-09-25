SOURCE = 'tags:\r\n  - alpha\r\n  -\tbeta\r\n  - gamma\r\n'
# Spec §7.5: `-\tbeta` is text; text at a List's level has nowhere to attach (§6.4) -> error.
SPEC = ('error', 'OutOfContextNodeError')
AUTHOR = {'tags': ['alpha', 'beta', 'gamma']}
