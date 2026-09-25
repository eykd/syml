Feature: Prose, dialogue, and headers are text, all the time
  Structure is decided at the first line of a block and at inline positions
  only. Once a value is text, every following line at or past its baseline
  is that value's text regardless of shape, a blank line between two such
  lines is a paragraph break, and `#`/`//` mark a comment only as the first
  characters of a line with no indentation. See spec.md User Story 1.

  Scenario: A blank line between two continuation lines is kept
    Given a SYML document "k:\n  Para one.\n\n  Para two."
    When it is parsed
    Then the result equals {"k": "Para one.\n\nPara two."}

  Scenario: A root scalar keeps a paragraph break
    Given a SYML document "Para one.\n\nPara two."
    When it is parsed
    Then the result is the scalar "Para one.\n\nPara two."

  Scenario: A continuation line shaped like a list item is text
    Given a SYML document "k:\n  some prose\n  - used as a dash\n  more"
    When it is parsed
    Then the result equals {"k": "some prose\n- used as a dash\nmore"}

  Scenario: An indented comment marker is text inside a list item
    Given a SYML document "- Share is\n  //server/share"
    When it is parsed
    Then the result equals ["Share is\n//server/share"]

  Scenario: An indented hash marker is text inside a list item
    Given a SYML document "- tag line\n  #winning"
    When it is parsed
    Then the result equals ["tag line\n#winning"]

  Scenario: A hash after an inline value is text
    Given a SYML document "port: 8080 # default"
    When it is parsed
    Then the result equals {"port": "8080 # default"}

  Scenario Outline: Structure-shaped list items are text
    Given a SYML document "<document>"
    When it is parsed
    Then the result equals <expected>

    Examples:
      | document                    | expected                     |
      | - [ask: why?]               | ["[ask: why?]"]               |
      | - "listen: I know."         | ["\"listen: I know.\""]       |
      | - 3: 1 odds                 | ["3: 1 odds"]                 |

  Scenario: A quoted root scalar stays text
    Given a SYML document "\"so: you came back.\""
    When it is parsed
    Then the result is the scalar "\"so: you came back.\""

  Scenario: Uppercase would-be keys are text
    Given a SYML document "env:\n  HOME: /h\n  PATH: /p"
    When it is parsed
    Then the result equals {"env": "HOME: /h\nPATH: /p"}

  Scenario: A same-column key with an uppercase character raises with a hint
    Given a SYML document "name: a\nfirstName: b\nage: 3"
    When it is parsed
    Then parsing raises OutOfContextNodeError at line 2 with a key-pattern hint

  Scenario: A text first line makes the whole document text
    Given a SYML document "Given:\n  a: 1"
    When it is parsed
    Then the result is the scalar "Given:\n  a: 1"

  Scenario Outline: A root scalar keeps its leading indentation
    Given a SYML document "<document>"
    When it is parsed
    Then the result is the scalar "<expected>"

    Examples:
      | document              | expected             |
      | \x20\x20hello          | \x20\x20hello         |
      | \x20\x20hello\nworld   | \x20\x20hello\nworld  |
      | \x20\x20hello\n\x20\x20\x20\x20world | \x20\x20hello\n\x20\x20\x20\x20world |

  Scenario: Blank lines between continuations are kept one for one and never trail
    Given a SYML document "k:\n  a\n\n\n  b\n\n"
    When it is parsed
    Then the result equals {"k": "a\n\n\nb"}

  Scenario: A blank line before the first continuation line is inert
    Given a SYML document "k:\n\n  a"
    When it is parsed
    Then the result equals {"k": "a"}

  Scenario: A blank line between a value and the next key stays inert
    Given a SYML document "k:\n  a\n\nb: 2"
    When it is parsed
    Then the result equals {"k": "a", "b": "2"}

  Scenario: Column-0 comments are skipped and an indented comment is a root scalar
    Given a SYML document "# one\n// two\n  # three"
    When it is parsed
    Then the result is the scalar "\x20\x20# three"

  Scenario: A comment-only document with no trailing newline is empty
    Given a SYML document "# c"
    When it is parsed
    Then the result is the scalar ""

  Scenario: An indented comment at a mapping's level still raises
    Given a SYML document "a:\n  b: 1\n  # note"
    When it is parsed
    Then parsing raises OutOfContextNodeError

  Scenario: An inline value followed by deeper lines of any shape stays one text value
    Given a SYML document "k: first\n  - second\n  key: third"
    When it is parsed
    Then the result equals {"k": "first\n- second\nkey: third"}

  Scenario: The first line of a block still decides structure for a list
    Given a SYML document "k:\n  - a\n  - b"
    When it is parsed
    Then the result equals {"k": ["a", "b"]}

  Scenario: The first line of a block still decides structure for a mapping
    Given a SYML document "k:\n  x: 1\n  y: 2"
    When it is parsed
    Then the result equals {"k": {"x": "1", "y": "2"}}

  Scenario: A below-baseline line ends a value and finds no context
    Given a SYML document "k: a\n    b\n  c"
    When it is parsed
    Then parsing raises OutOfContextNodeError

  Scenario: A column-0 hash header line is a comment
    Given a SYML document "# Application config\nname: app\nport: 80"
    When it is parsed
    Then the result equals {"name": "app", "port": "80"}

  Scenario: A column-0 double-slash header line is a comment
    Given a SYML document "// header\nname: app"
    When it is parsed
    Then the result equals {"name": "app"}

  Scenario: A column-0 comment between two lines of an open value is skipped, not a paragraph break
    Given a SYML document "k:\n  a\n# note\n  b"
    When it is parsed
    Then the result equals {"k": "a\nb"}

  Scenario: Physical blanks around a skipped comment still count one for one
    Given a SYML document "k:\n  a\n\n# note\n\n  b"
    When it is parsed
    Then the result equals {"k": "a\n\n\nb"}

  Scenario: A single physical blank around a skipped comment counts once
    Given a SYML document "k:\n  a\n\n# note\n  b"
    When it is parsed
    Then the result equals {"k": "a\n\nb"}

  Scenario: An indented hash line inside a block value is text
    Given a SYML document "k:\n  a\n  # note\n  b"
    When it is parsed
    Then the result equals {"k": "a\n# note\nb"}

  Scenario: A trailing hash after a key's colon is that key's inline text value
    Given a SYML document "server: # prod\n  host: x"
    When it is parsed
    Then the result equals {"server": "# prod\nhost: x"}

  Scenario: A column-0 comment inside a root scalar is dropped
    Given a SYML document "hello\n# note\nworld"
    When it is parsed
    Then the result is the scalar "hello\nworld"

  Scenario: A comment before a root scalar's first line does not take its place
    Given a SYML document "# c\n  hello"
    When it is parsed
    Then the result is the scalar "\x20\x20hello"

  Scenario: A BOM-stripped header line is still a column-0 comment
    Given a SYML document "\ufeff# header\nk: v"
    When it is parsed
    Then the result equals {"k": "v"}

  Scenario: A BOM anywhere else is content, not a comment marker
    Given a SYML document "a: 1\n\ufeff# x"
    When it is parsed
    Then parsing raises OutOfContextNodeError

  Scenario: A 0.6.2-style comment between entries still works
    Given a SYML document "a: 1\n# note\nb: 2"
    When it is parsed
    Then the result equals {"a": "1", "b": "2"}
