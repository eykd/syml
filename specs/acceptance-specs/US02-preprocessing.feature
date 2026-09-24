Feature: Pre-processing and line splitting match section 9.0 and 13.3
  A document is normalized before any other rule runs: a leading byte-order
  mark is stripped, CRLF and bare CR line endings are collapsed to LF, a tab
  in indentation is a named error, and only LF terminates a line.

  Scenario: Exactly one leading byte-order mark is stripped
    Given a SYML document "\ufeffkey: value"
    When it is parsed
    Then the result equals {'key': 'value'}

  Scenario: A document consisting only of a byte-order mark is the empty document
    Given a SYML document "\ufeff"
    When it is parsed
    Then the result is the empty string

  Scenario: CRLF line endings are collapsed to LF
    Given a SYML document "a: b\\r\\nc: d"
    When it is parsed
    Then the result equals {'a': 'b', 'c': 'd'}

  Scenario: A bare carriage return is collapsed to LF
    Given a SYML document "a: b\\rc: d"
    When it is parsed
    Then the result equals {'a': 'b', 'c': 'd'}

  Scenario: A tab in indentation is a named error
    Given a SYML document "\\tkey: value"
    When it is parsed
    Then parsing fails with "TabIndentationError"

  Scenario: A continuation line gets no exemption from the tab check
    Given a SYML document "key: a\\n\\tb"
    When it is parsed
    Then parsing fails with "TabIndentationError"

  Scenario: A whitespace-only line is blank and discarded before the tab check
    Given a SYML document "key: value\\n \\t \\nnext: value"
    When it is parsed
    Then the result equals {'key': 'value', 'next': 'value'}

  Scenario: Only LF terminates a line, so U+2028 stays inside the value
    Given a SYML document "a: b\\u2028c\\nx: y"
    When it is parsed
    Then the result equals {'a': 'b\u2028c', 'x': 'y'}
