Feature: Source tracking is a supported surface with original-text positions
  An editor integration parses a document and wants to place a cursor on the
  exact character a value came from in the original file, byte-order mark,
  carriage returns, and all.

  Scenario: as_source returns Source objects and as_data returns equivalent plain values
    Given a SYML document "a: 1\\nb: 2"
    When it is parsed with source tracking
    Then every leaf of as_source is a Source carrying a filename and start and end positions
    And as_data returns the equivalent plain strings, lists, and mappings

  Scenario: A position after a leading byte-order mark counts the mark
    Given a SYML document "\ufeffkey: value"
    When it is parsed with source tracking
    Then the value's position locates it in the original text, counting the mark

  Scenario: A position after CRLF line endings counts each carriage return
    Given a SYML document "a: b\\r\\nc: d"
    When it is parsed with source tracking
    Then the value's position locates it in the original text, counting each carriage return

  Scenario: A position after a U+2028 line separator reports the correct line number
    Given a SYML document "a: b\\u2028c\\nx: y"
    When it is parsed with source tracking
    Then "x"'s position reports line 2

  Scenario: The source-tracking surface is covered by tests, not exempted from coverage
    Given the released library
    When the source-tracking surface is exercised
    Then it is covered by tests rather than exempted from the coverage gate
