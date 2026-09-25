SOURCE = ('﻿name: widget  \r\n'      # trailing spaces after a value
          'tags: \r\n'                    # trailing space after key:
          '  - alpha\r\n'
          '  - \r\n'                      # marker + trailing space
          '  - gamma\t\r\n'               # trailing tab
          'note: a\tb\r\n'                # tab inside value
          'empty:   \r\n')                # trailing spaces after section
# Spec: BOM/CRLF normalized (§9.0); value trailing ws preserved (§7.5); `tags: ` -- UNSURE: §4.1 grammar says
# key_value(ws, data="") i.e. an inline empty value that closes the key, so the nested list would then be
# out of context. Prediction (hedged): implementation normalizes zero-length inline like `- ` (§7.3/§9.3).
SPEC = {'name': 'widget  ', 'tags': ['alpha', '', 'gamma\t'], 'note': 'a\tb', 'empty': ''}
AUTHOR = {'name': 'widget', 'tags': ['alpha', '', 'gamma'], 'note': 'a\tb', 'empty': ''}
