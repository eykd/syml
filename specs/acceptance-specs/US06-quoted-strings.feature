Feature: Quoted strings work exactly where section 4.7 says they do
  Quoting is the only way to write a value with leading spaces, an embedded
  newline, or a literal backslash, and an apostrophe at the start of a bare
  prose line stays prose.

  Scenario: A double-quoted value preserves leading and trailing spaces
    Given a SYML document "padded: \"  hello  \""
    When it is parsed
    Then the result equals {'padded': '  hello  '}

  Scenario: A single-quoted value does not decode backslash escapes
    Given a SYML document "literal: 'hello\\nworld'"
    When it is parsed
    Then the result equals {'literal': 'hello\nworld'}

  Scenario: A doubled single quote decodes to one literal apostrophe
    Given a SYML document "with_quote: 'it''s fine'"
    When it is parsed
    Then the result equals {'with_quote': "it's fine"}

  Scenario: A double-quoted escape sequence decodes to a real line feed
    Given a SYML document "escaped: \"hello\\nworld\""
    When it is parsed
    Then the result equals {'escaped': 'hello\nworld'}

  Scenario: An unterminated quoted value is malformed
    Given a SYML document "key: \"unterminated"
    When it is parsed
    Then parsing fails with "MalformedQuotedStringError"

  Scenario: Trailing text after a closing quote is malformed
    Given a SYML document "key: \"a\" trailing"
    When it is parsed
    Then parsing fails with "MalformedQuotedStringError"

  Scenario: An invalid escape sequence is malformed
    Given a SYML document "k: \"a\\xb\""
    When it is parsed
    Then parsing fails with "MalformedQuotedStringError"

  Scenario: A decoded surrogate code point is malformed
    Given a SYML document "k: \"\\ud800\""
    When it is parsed
    Then parsing fails with "MalformedQuotedStringError"

  Scenario: A code point above the Unicode maximum is malformed
    Given a SYML document "k: \"\\U00110000\""
    When it is parsed
    Then parsing fails with "MalformedQuotedStringError"

  Scenario: A quoted value is complete and accepts no continuation
    Given a SYML document "key: \"a\"\\n  b"
    When it is parsed
    Then parsing fails with "OutOfContextNodeError"

  Scenario: Quoting is not recognized on a bare root-scalar line
    Given a SYML document "\"unterminated"
    When it is parsed
    Then the result is the scalar "\"unterminated"

  Scenario: A continuation line does not quote-decode
    Given a SYML document "key: He said\\n  'yes'"
    When it is parsed
    Then the result equals {'key': "He said\n'yes'"}
