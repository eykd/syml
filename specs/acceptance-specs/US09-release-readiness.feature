Feature: A release-ready main with migration notes and one conformance ledger
  A 0.6.2 user upgrading to 1.0.0 finds every behavior change in one place,
  and a contributor finds one statement of where the parser stands against
  the specification.

  Scenario: The specification header is labelled version 1.0
    Given SYML-SPECIFICATION.md
    When its header is read
    Then it is labelled version 1.0 and names syml 1.0.0 as the conforming reference implementation
    And the review pass and the release are folded into a single version-history entry

  Scenario: The migration notes list every user-visible change
    Given the migration notes
    When a 0.6.2 user reads them
    Then they list the null-to-empty-string change, tabs and duplicate keys becoming errors, quoted values decoding, the leading-marker and key-colon-value fallthrough, third-party parser exceptions no longer escaping, the new load input types, and the new dumps and dump

  Scenario: Exactly one conformance ledger exists
    Given the repository
    When it is searched for a conformance ledger
    Then todo.txt is retired or rewritten with no conformance claim, and CLAUDE.md's "Spec vs. implementation" section says the parser conforms

  Scenario: Importing syml emits no warning
    Given a fresh environment
    When syml is imported
    Then no warning is emitted

  Scenario: The node-tree test module holds real tests
    Given the node-tree test module
    When it is inspected
    Then it holds real tests rather than being empty, and the dead statement in Source's concatenation operator is gone

  Scenario: The constitution's principle IV reflects the released state
    Given the constitution
    When principle IV is read
    Then it no longer claims the specification is aspirational or that todo.txt is the conformance ledger
    And it permits a specification edit that lands in the same commit as the behavior change it exposed
    And the constitution version is bumped per its own Governance Amendment Procedure and Versioning Policy

  Scenario: The plan's Constitution Check section documents the breaking changes
    Given the plan's Constitution Check section
    When it is read
    Then it lists Pos moving to original-text coordinates, load accepting binary streams, and the resulting 1.0.0 major version bump, each paired with the non-breaking alternative it rejected
