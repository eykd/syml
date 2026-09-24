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
      | empty_mapping_value |
      | empty_list_item |
      | contains_newline |
      | contains_newline_list_item |
      | contains_newline_root_scalar |
      | contains_newline_nested_indent |
      | contains_newline_nested_mapping |
      | tab_inside_value |
      | trailing_space |
      | dialogue_with_quotes |
      | leading_apostrophe |
      | quote_then_text |
      | listen_prose_list_item |
      | listen_prose_root_scalar |
      | looks_like_key_value_as_mapping_value |
      | looks_like_key_value_no_space |
      | looks_like_key_value_no_space_as_mapping_value |
      | looks_like_list_item_as_mapping_value |
      | looks_like_negative_number |
      | starts_with_single_quote |
      | starts_with_double_quote |
      | starts_with_hash |
      | starts_with_slashslash |
      | literal_single_quotes |
      | literal_double_quotes |
      | colon_escape_list_item_as_mapping_value |
      | literal_backslash_u003a_as_mapping_value |
      | mixed_quote_backslash_as_mapping_value |
      | stranded_double_quote_as_mapping_value |
      | stranded_single_quote_as_mapping_value |
      | deep_dash_run_mapping_value |
      | astral_plane_char |
      | combining_char |
      | nested_depth_4 |
      | list_of_mappings |
      | insertion_order_mapping |
      | lowercase_roman_numeral_key |
      | leading_feff_root_scalar |
      | leading_feff_first_key |

  Scenario Outline: An unrepresentable value raises UnrepresentableValueError
    Given the unrepresentable corpus value "<corpus_id>"
    When it is serialized
    Then serializing fails with "UnrepresentableValueError"

    Examples:
      | corpus_id |
      | leading_trailing_space |
      | leading_trailing_tab |
      | leading_space_root_scalar |
      | contains_cr |
      | contains_nul |
      | contains_blank_line |
      | block_line_begins_with_tab |
      | block_line_begins_with_comment_marker |
      | block_line_lexes_as_structure |
      | looks_like_key_value |
      | looks_like_list_item |
      | bare_dash_list_item |
      | colon_escape_list_item |
      | literal_backslash_u003a |
      | mixed_quote_backslash |
      | stranded_double_quote |
      | stranded_single_quote |
      | deep_dash_run_list_item |
      | deep_dash_run_root_scalar |
      | comment_marker_root_scalar |
      | uppercase_key |
      | titlecase_key |
      | control_x01_key |
      | control_x7f_key |
      | control_x9f_key |
      | control_x1c_key |
      | nbsp_key |
      | line_separator_key |

  Scenario: A string containing a line feed is written in block form and reads back identically
    Given a mapping value containing a line feed
    When it is serialized
    Then the key stands alone on its line, each line of the value follows indented two spaces deeper, and loads reads the output back identically

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
    Given a key containing whitespace, a colon, or an uppercase letter, the empty-string key, or a key beginning with "#" or "//"
    When it is serialized
    Then serializing fails with "UnrepresentableValueError"

  Scenario: A root scalar with no encoding is unrepresentable
    Given a root scalar that would lex as structure, begins with a comment marker, holds a control character other than tab, has leading whitespace on its first line, or contains a blank line
    When it is serialized
    Then serializing fails with "UnrepresentableValueError"

  Scenario: A value written with dump is read back identically with load
    Given a value written to an open file handle with dump
    When that file is read back with load
    Then the result equals the original value
