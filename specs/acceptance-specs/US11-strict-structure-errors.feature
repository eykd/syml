Feature: Structure is strict, whitespace is honest, and errors say why
  Children are strictly deeper than their parent, a tab after a marker is
  ordinary separator whitespace, only U+0020 is indentation, and a context
  error names the file, line, column, the columns that were open, and a
  one-line hint when one applies. See spec.md User Story 2.

  Scenario: A list at its key's column raises with an indentation hint
    Given a SYML document "k:\n- a\n- b"
    When it is parsed
    Then parsing raises OutOfContextNodeError with an indentation hint

  Scenario Outline: A child must be strictly deeper than its parent
    Given a SYML document "<document>"
    When it is parsed
    Then parsing raises OutOfContextNodeError

    Examples:
      | document                       |
      | a:\n- x\n- y\nb: z              |
      | - key:\n  - x                   |

  Scenario: The inline key sets the sibling column
    Given a SYML document "- server:\n  host: x"
    When it is parsed
    Then the result equals [{"server": "", "host": "x"}]

  Scenario Outline: A tab after a marker is separator whitespace
    Given a SYML document "<document>"
    When it is parsed
    Then the result equals <expected>

    Examples:
      | document              | expected                |
      | k:\tv                  | {"k": "v"}                |
      | a:\t\n  b: 1           | {"a": {"b": "1"}}          |
      | - a\n-\tx              | ["a", "x"]                 |

  Scenario: A tab in leading indentation still raises TabIndentationError
    Given a SYML document "a:\n\tb"
    When it is parsed
    Then parsing raises TabIndentationError

  Scenario: A non-breaking space is content, not a key line
    Given a SYML document "\xa0k: v"
    When it is parsed
    Then the result is the scalar "\xa0k: v"

  Scenario: A non-breaking-space-only line below a value's baseline raises
    Given a SYML document "k:\n  a\n\xa0\n  b"
    When it is parsed
    Then parsing raises OutOfContextNodeError

  Scenario Outline: Non-space whitespace characters pass through verbatim
    Given a SYML document "<document>"
    When it is parsed
    Then the result is the scalar "<expected>"

    Examples:
      | document      | expected      |
      | \x0bx          | \x0bx          |
      | \x0c           | \x0c           |
      | \u2028- x      | \u2028- x      |

  Scenario: An out-of-context error names the failing column and every open column
    Given a SYML document "k:\n  a: 1\n b: 2"
    When it is parsed
    Then parsing raises OutOfContextNodeError whose string form starts "3:1: " naming open columns 0 and 2

  Scenario: The filename prefixes both the printed form and the message
    Given a SYML document "k:\n  a: 1\n b: 2" loaded with filename "f.syml"
    When it is parsed
    Then parsing raises an error whose string form starts "f.syml:3:1: " and whose message starts "f.syml: "

  Scenario Outline: Every ParseError subclass carries the filename prefix
    Given a SYML document "<document>" loaded with filename "f.syml"
    When it is parsed
    Then parsing raises an error whose message starts "f.syml: "

    Examples:
      | document      |
      | a: 1\n- x      |
      | a:\n\tb        |

  Scenario: A TabIndentationError position is in the caller's original-text coordinates
    Given a SYML document "a: 1\r\n\tb: 2"
    When it is parsed
    Then parsing raises TabIndentationError at index 6, line 2, column 0

  Scenario: A BOM-led document also reports original-text tab coordinates
    Given a SYML document "\ufeff\tk: v"
    When it is parsed
    Then parsing raises TabIndentationError at index 1, line 1, column 1

  Scenario: BOM and CRLF are both accounted for in the tab position
    Given a SYML document "\ufeffa: b\r\n\tc: d"
    When it is parsed
    Then parsing raises TabIndentationError at index 7, line 2, column 0

  Scenario: A non-breaking-space-led line is content, so a later tab is not indentation
    Given a SYML document "key: v\n\xa0\tx"
    When it is parsed
    Then parsing raises OutOfContextNodeError
