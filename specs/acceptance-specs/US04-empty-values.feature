Feature: Absent values are the empty string, never a null
  Every leaf value is a plain string: an empty document, a comment-only
  document, and a valueless key all yield the empty string, never a
  language-level null.

  Scenario: A valueless key yields the empty string
    Given a SYML document "empty:\\nnext: value"
    When it is parsed
    Then the result equals {'empty': '', 'next': 'value'}

  Scenario: The empty document yields the empty string
    Given the empty document
    When it is parsed
    Then the result is the empty string

  Scenario: A comment-only document yields the empty string
    Given a SYML document "# just a comment"
    When it is parsed
    Then the result is the empty string

  Scenario: A trailing space after a valueless key still yields the empty string
    Given a SYML document "key: "
    When it is parsed
    Then the result equals {'key': ''}

  Scenario: No leaf of any accepted document is ever a null
    Given a SYML document "a:\\n  b: value\\nc:\\n  - x\\n  - y"
    When it is parsed
    Then no leaf value in the result is a null of any kind
