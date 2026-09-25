Feature: The documents describe exactly what ships, and 1.0.0 is tagged
  The specification, the review document's decision table, the changelog,
  and the README agree with the code, and the 1.0.0 tag is pushed. See
  spec.md User Story 4.

  Scenario: Every specification example produces exactly its stated output
    Given the revised SYML-SPECIFICATION.md
    When every fenced syml block that states an Output or an ERROR is run
    Then each produces exactly that output or raises exactly that error

  Scenario: The printed grammar matches the grammar the parser declares
    Given the grammar printed in specification section 4.1
    When it is compared with the grammar the parser declares
    Then the two are the same rule set

  Scenario: The review document records the new decisions and their supersessions
    Given SYML-SPEC-REVIEW.md
    When it is read
    Then decisions D20 through D25 record the key pattern, text context, paragraph breaks, column-0-only comments, tab as separator, and strict indentation, each with the alternative not taken and a breaking-change note
    And decisions D5, D12, D13, D15, and D19 are annotated in place as superseded

  Scenario: The changelog's 1.0.0 entry describes what master does
    Given CHANGELOG.md's 1.0.0 entry
    When it is read by a 0.6.2 user
    Then items 4, 7, 10, 12, 13, 16, and 17 describe what master does
    And new items state the column-0-only comment rule, the key pattern, that values are text throughout, that blank lines inside values are kept, that indentless sequences are rejected, and that a tab after a marker is separator whitespace

  Scenario: The README documents coming from YAML
    Given the README
    When it is read
    Then a "Coming from YAML" section lists, in order, comments only at column 0, no block-scalar indicators, no document markers, no quoting, that null/true/123/tilde/lists/mappings written inline are plain strings, the key pattern, that a key or list marker needs a space after it, the sibling-column rule, paragraph breaks, and that trailing whitespace is kept and over-indented lines join the value above

  Scenario: Every documented exception class is exported
    Given specification section 11.3
    When it is compared with the package's exports
    Then every class the spec says MUST exist is exported
    And every exported error class is listed

  @release
  Scenario: The 1.0.0 tag is pushed to the remote
    Given the release
    When git ls-remote --tags origin is run
    Then 1.0.0 is present and points at the commit that carries the revised spec, code, changelog, and README

  Scenario: The public docs for Source state its semantics
    Given the public docs for Source
    When they are read
    Then they state that Source is not a str, that an empty Source is truthy, and that a multi-line Source.text is the dedented value as_data returns
