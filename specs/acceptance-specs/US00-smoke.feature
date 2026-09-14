Feature: Parse a minimal SYML document
  The committed reference example for the pytest-bdd pipeline. Real feature
  specs are written by /sp:05-tasks as US<NN>-<slug>.feature and bound in
  tests/acceptance/test_us<nn>_<slug>.py.

  Scenario: A single key-value line becomes a one-entry mapping
    Given a SYML document containing "name: syml"
    When it is parsed
    Then the result is a mapping with key "name" and value "syml"
