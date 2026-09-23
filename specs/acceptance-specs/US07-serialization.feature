Feature: Round-trip serialization with dumps and dump
  A tool that reads a SYML config, edits a value, and writes it back needs a
  serializer whose output the parser reads back identically.

  Scenario Outline: A representable value round-trips through dumps and loads
    Given the representable corpus value "<corpus_id>"
    When it is serialized with dumps and re-read with loads
    Then the result equals the original value

    Examples:
      | corpus_id |
      | empty_string |
      | leading_trailing_space |
      | leading_trailing_tab |
      | contains_newline |
      | contains_cr |
      | contains_nul |
      | looks_like_key_value |
      | looks_like_key_value_no_space |
      | looks_like_list_item |
      | looks_like_negative_number |
      | starts_with_single_quote |
      | starts_with_double_quote |
      | starts_with_hash |
      | starts_with_slashslash |
      | literal_single_quotes |
      | literal_double_quotes |
      | colon_escape_list_item |
      | literal_backslash_u003a |
      | mixed_quote_backslash |
      | stranded_double_quote |
      | stranded_single_quote |
      | deep_dash_run_list_item |
      | deep_dash_run_mapping_value |
      | astral_plane_char |
      | combining_char |
      | nested_depth_4 |
      | list_of_mappings |
      | insertion_order_mapping |
      | leading_feff_root_scalar |
      | leading_feff_first_key |

  Scenario: A string needing quoting because of whitespace or control characters is quoted
    Given a string with leading or trailing whitespace, or containing a line feed, a carriage return, or another control character
    When it is serialized
    Then it is emitted quoted, and a line feed is emitted as an escape rather than as block continuation

  Scenario: Single-quoting is preferred over double-quoting when no control character is present
    Given a value that needs quoting and holds no control characters
    When it is serialized
    Then single-quoting is used in preference to double-quoting

  Scenario: A list item holding a mapping is separated from its marker by exactly one space
    Given a list item whose value is a mapping
    When it is serialized
    Then exactly one space separates the marker from the key

  Scenario: Mapping keys are serialized in insertion order
    Given a mapping with keys in a specific insertion order
    When it is serialized
    Then its keys appear in that same order in the output

  Scenario: An empty list or empty mapping at any depth is unrepresentable
    Given a structure containing an empty list or an empty mapping at any depth
    When it is serialized
    Then serializing fails with "UnrepresentableValueError"

  Scenario: A key with no encoding is unrepresentable
    Given a key containing whitespace or a colon, the empty-string key, or a key beginning with "#" or "//"
    When it is serialized
    Then serializing fails with "UnrepresentableValueError"

  Scenario: A root scalar with no encoding is unrepresentable
    Given a root scalar that would lex as structure, begins with a comment marker, holds a control character, has leading or trailing whitespace on a line, or is exactly two quote characters
    When it is serialized
    Then serializing fails with "UnrepresentableValueError"

  Scenario: A value written with dump is read back identically with load
    Given a value written to an open file handle with dump
    When that file is read back with load
    Then the result equals the original value
