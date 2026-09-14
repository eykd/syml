# Gherkin Spec Writing Guide

## Format Syntax

### File Structure

```gherkin
Feature: Parsing nested lists
  A SYML document can contain a list whose items are themselves lists or
  mappings, nested by indentation.

  Scenario: A nested list preserves document order
    Given a SYML document with a nested list
    When it is parsed
    Then the list items are returned in document order

  Scenario: A list item that is itself a mapping is preserved
    Given a SYML document with a list item that is a key-value mapping
    When it is parsed
    Then that list item is a mapping with the expected key and value
```

### Rules

- **`Feature:`** — one line naming the user story, followed by an indented narrative of a sentence or two (who wants this, why it matters)
- **`Scenario:`** — one line describing a single, independently-runnable case
- **Steps**: `Given`, `When`, `Then`, continued with `And`/`But` — capitalized, one per line, no trailing period required
- **Blank lines**: allowed between scenarios, ignored by the parser
- **`Scenario Outline:` + `Examples:`**: parameterize one scenario shape over a table of rows — use when the same Given/When/Then structure repeats with only the values changing
- **One feature file per user story**: `US<NN>-<kebab-case-title>.feature`

### Multi-Scenario Files

A single feature file can contain multiple scenarios. Each scenario binds to one pytest-bdd test function at collection time. Use multiple scenarios to cover variations of the same user story: the happy path, edge cases, and error cases as separate, independent scenarios.

## Domain Language Discipline

Specs must use the vocabulary of **SYML documents and what parsing them produces**, never the vocabulary of the parser's implementation.

### SYML Domain Vocabulary

| Say this                                              | NOT this                                              |
| ------------------------------------------------------ | ------------------------------------------------------ |
| a SYML document containing a key-value line             | a `KeyValue` node in the grammar                        |
| the document is parsed                                  | `SymlParser.parse` is called                            |
| the result is a mapping with key "X" and value "Y"      | `as_data()` returns a dict with key "X"                 |
| the list items are returned in document order            | the `Mapping`/`List` intermediary preserves item order  |
| a multiline value spanning two lines                     | a `TextLeafNode` accepts a second `TextLeafNode` child  |
| parsing fails with an out-of-context error naming line 2 | `OutOfContextNodeError` is raised by `incorporate_node` |
| the value carries its source position                    | `Source.from_node` returns a `Source` dataclass         |

### Good/Bad Examples

**1. Describing preconditions**

Good:

```gherkin
Given a SYML document with a nested list
```

Bad:

```gherkin
Given a Parsimonious grammar match for an indented ListItem
```

**2. Describing the action**

Good:

```gherkin
When it is parsed
```

Bad:

```gherkin
When SymlParser.visit_lines walks the flat list of line nodes
```

**3. Describing outcomes**

Good:

```gherkin
Then the list items are returned in document order
Then the second item is "bar"
```

Bad:

```gherkin
Then as_data() returns ['foo', 'bar', 'baz']
Then the ContainerNode has three children
```

**4. Describing errors**

Good:

```gherkin
Given a document whose second line is indented deeper than any open container
When it is parsed
Then parsing fails with an out-of-context error naming line 2
```

Bad:

```gherkin
When the parser is called
Then OutOfContextNodeError is raised with a Pos(line=2) argument
```

**5. Multi-step setup with Scenario Outline**

Good:

```gherkin
Scenario Outline: A simple mapping round-trips through the parser
  Given a SYML document containing "<line>"
  When it is parsed
  Then the result is a mapping with key "<key>" and value "<value>"

  Examples:
    | line          | key    | value |
    | name: syml    | name   | syml  |
    | color: blue   | color  | blue  |
```

Bad:

```gherkin
Given a document is loaded via syml.loads("name: syml")
Then the dict equals {"name": "syml"}
```

## Spec Review Checklist

Before committing a spec file, verify:

1. **File name** matches `specs/acceptance-specs/US<NN>-<kebab-case-title>.feature`
2. **`Feature:`** line has a short narrative underneath it
3. **Keywords** are `Given`/`When`/`Then`/`And`/`But`, capitalized, at the start of the line
4. **No implementation language** — no class/function/module names, no grammar or parser-internals vocabulary, no exception class names in step text
5. **Scenarios are independent** — each can run alone, in any order (the unit suite runs randomized; keep acceptance scenarios equally order-independent)
6. **Outcomes are observable** — describe what `syml.loads`/`syml.load` return or raise, not internal parse-tree shape
7. **Error cases are covered** — include at least one scenario for a malformed document
8. **`Scenario Outline`** is used instead of copy-pasted near-duplicate scenarios whenever only the values differ
