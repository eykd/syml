Feature: A complete, catchable error taxonomy and a stable entry API
  An embedding application can catch a single base class, distinguish the
  failure kinds, read the position and offending line off the exception, and
  hand load a text or binary file handle.

  Scenario: The six exception classes resolve with the specified inheritance
    Given the installed library
    When "ParseError", "OutOfContextNodeError", "DuplicateKeyError", "TabIndentationError", "UnrepresentableValueError", and "EncodingError" are imported from syml
    Then all six resolve and their inheritance matches section 11.3 as amended

  Scenario: A document that used to leak a third-party exception now parses cleanly
    Given a SYML document "key:value"
    When it is parsed
    Then the result is the scalar "key:value"

  Scenario: No third-party parser exception escapes any document in the audit's failing set
    Given every document in the audit's failing set
    When each is passed to loads
    Then any exception raised is a ParseError and no third-party parser exception escapes

  Scenario: Every ParseError carries message, position, and line text
    Given a SYML document "key:\\n  first\\n    indented\\n  back\\nb"
    When it is parsed
    Then parsing fails with "OutOfContextNodeError"
    And the exception's "message", "position", and "line_text" are readable as named attributes

  Scenario: A DuplicateKeyError carries the repeated key and the first occurrence's position
    Given a SYML document "key: value1\\nkey: value2"
    When it is parsed
    Then parsing fails with "DuplicateKeyError"
    And the exception also carries the repeated key and the first occurrence's position

  Scenario: A binary handle over valid UTF-8 parses the same as the equivalent text handle
    Given a binary file handle over the UTF-8 bytes of "key: value"
    And a text file handle over "key: value"
    When each is passed to load
    Then both results are equal

  Scenario: A binary handle over invalid UTF-8 raises EncodingError
    Given a binary file handle over bytes that are not valid UTF-8
    When it is passed to load
    Then parsing fails with "EncodingError"
    And no replacement characters or unpaired surrogates appear in any result
