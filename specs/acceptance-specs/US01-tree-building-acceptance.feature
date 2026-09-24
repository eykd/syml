Feature: Tree building follows the specification's acceptance rules
  A configuration author writes a nested document; indentation that does not
  exactly match a registered sibling level is rejected, a key-value pair or
  list item that already holds a value refuses further content, and a
  multiline value keeps the indentation the author wrote.

  Scenario: Siblings must match on exact indentation, not at least as deep
    Given a SYML document "parent:\\n  child1: value\\n child2: value"
    When it is parsed
    Then parsing fails with "OutOfContextNodeError"

  Scenario: An inline value closes its pair to further content
    Given a SYML document "note: hello\\n  more: text"
    When it is parsed
    Then parsing fails with "OutOfContextNodeError"

  Scenario: A multiline value's first own-line sets the baseline
    Given a SYML document "key:\\n  first\\n    indented\\n  back"
    When it is parsed
    Then the result equals {'key': 'first\n  indented\nback'}

  Scenario: A line no deeper than its key is not a continuation
    Given a SYML document "key: a\\nb"
    When it is parsed
    Then parsing fails with "OutOfContextNodeError"

  Scenario: A line below the fixed baseline terminates the value and finds no context
    Given a SYML document "key: a\\n    b\\n  c"
    When it is parsed
    Then parsing fails with "OutOfContextNodeError"

  Scenario: A root scalar's baseline is fixed at column zero
    Given a SYML document "hello\\n  world\\nagain"
    When it is parsed
    Then the result equals 'hello\n  world\nagain'

  Scenario: Plain text at a container's own level is not a value
    Given a SYML document "a:\\n  b: 1\\n  plain"
    When it is parsed
    Then parsing fails with "OutOfContextNodeError"

  Scenario: An inline key's own column, not the line's indentation, sets the sibling column
    Given a SYML document "-   name: Alice\\n  role: admin"
    When it is parsed
    Then parsing fails with "OutOfContextNodeError"

  Scenario: A duplicate key is rejected the moment the second pair is incorporated
    Given a SYML document "key: value1\\nkey: value2"
    When it is parsed
    Then parsing fails with "DuplicateKeyError"

  Scenario: An invalid key joins the previous value as prose instead of becoming a mapping
    Given a SYML document "a: Note\\n  Big Warning: do not touch"
    When it is parsed
    Then the result equals {'a': 'Note\nBig Warning: do not touch'}
