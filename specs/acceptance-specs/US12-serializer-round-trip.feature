Feature: The serializer writes everything the parser reads
  dumps writes every value the revised grammar makes loadable, reads Source
  keys and scalars as their text, and refuses only the residual families
  named in FR-006. See spec.md User Story 3.

  Scenario: A paragraph break round-trips in block form
    Given the value {"k": "Para one.\n\nPara two."}
    When it is dumped and loaded again
    Then the value round-trips unchanged

  Scenario: A structure-shaped later line round-trips unrestricted
    Given the value {"k": "some prose\n- used as a dash\nkey: v"}
    When it is dumped and loaded again
    Then the value round-trips unchanged

  Scenario: An indented root scalar is written in block form at column 0
    Given the scalar "\x20\x20hello\nworld"
    When it is dumped
    Then the output is "\x20\x20hello\nworld\n" and it loads back to the same string

  Scenario Outline: A value with no spelling is refused
    Given the value <value>
    When it is dumped
    Then dumping raises UnrepresentableValueError

    Examples:
      | value        |
      | ["- x"]       |
      | ["a: 1"]      |
      | ["\n"]        |

  Scenario Outline: A line that only looks like structure after BOM stripping is content
    Given the value <value>
    When it is dumped and loaded again
    Then the value round-trips unchanged

    Examples:
      | value                          |
      | ["﻿- x"]                   |
      | {"k": "a\n﻿- x"}            |

  Scenario Outline: A leading non-breaking space is content everywhere
    Given the value <value>
    When it is dumped and loaded again
    Then the value round-trips unchanged

    Examples:
      | value                    |
      | ["\xa0x"]                 |
      | "\xa0x"                   |
      | {"k": "a\n\xa0b"}          |

  Scenario Outline: A key outside the key pattern is refused
    Given the value <value>
    When it is dumped
    Then dumping raises UnrepresentableValueError

    Examples:
      | value              |
      | {"Name": "x"}       |
      | {"1st": "x"}        |
      | {"e.mail": "x"}     |
      | {"名前": "x"}        |
      | {"": "x"}           |

  Scenario Outline: A conforming key is written
    Given the value <value>
    When it is dumped and loaded again
    Then the value round-trips unchanged

    Examples:
      | value                     |
      | {"first-name": "x"}        |
      | {"first_name": "x"}        |
      | {"choice1": "x"}           |

  Scenario: A Source key or scalar is written as its text
    Given the parsed source of "k: v"
    When it is dumped
    Then the output is "k: v\n"

  Scenario: The empty string dumps and loads as the empty document
    Given the empty string
    When it is dumped
    Then the output is the empty document and it loads back to the empty string

  Scenario: A carriage return has no spelling
    Given the value {"k": "\r"}
    When it is dumped
    Then dumping raises UnrepresentableValueError

  Scenario: A tab inside a value is written literally
    Given the value {"k": "a\tb"}
    When it is dumped and loaded again
    Then the value round-trips unchanged
