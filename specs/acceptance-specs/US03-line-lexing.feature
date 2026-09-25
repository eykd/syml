Feature: Lines lex per the section 4.1 grammar as printed
  Each line lexes exactly as the printed grammar says: structural forms
  require their guard, and anything that is not a complete structural form
  falls through to scalar text.

  Scenario: A bare list marker takes its item from the next line
    Given a SYML document "-\\n  block item"
    When it is parsed
    Then the result equals ['block item']

  Scenario: A marker followed by one space and nothing else is an empty item
    Given a SYML document "- "
    When it is parsed
    Then the result equals ['']

  Scenario: A colon with no following space is not a key-value pair
    Given a SYML document "key:value"
    When it is parsed
    Then the result is the scalar "key:value"

  Scenario: A hyphen with no following space is not a list marker
    Given a SYML document "-item"
    When it is parsed
    Then the result is the scalar "-item"

  Scenario: A leading hyphen on a negative number is not a list marker
    Given a SYML document "-42"
    When it is parsed
    Then the result is the scalar "-42"

  Scenario: A tab immediately after the colon is separator whitespace (D24)
    Given a SYML document "key:\\tv"
    When it is parsed
    Then the result equals {'key': 'v'}

  Scenario: A tab after the separating space is also separator whitespace (D24)
    Given a SYML document "key: \\tv"
    When it is parsed
    Then the result equals {'key': 'v'}

  Scenario: A trailing space after a valueless key does not change the result
    Given a SYML document "key: \\n  nested: content"
    When it is parsed
    Then the result equals {'key': {'nested': 'content'}}

  Scenario: A whitespace-only line never affects indentation
    Given a SYML document "a:\\n        \\n  b: c\\n  d: e"
    When it is parsed
    Then the result equals {'a': {'b': 'c', 'd': 'e'}}

  Scenario: A key excludes control characters and the Unicode whitespace set
    Given a SYML document "a\\x01b: v"
    When it is parsed
    Then the result is the scalar "a\x01b: v"
