---
name: refactoring
description: 'Use when: (1) tests are green and code needs improvement, (2) code smells detected during review, (3) preparing code for new features, (4) reducing technical debt. REQUIRED during Refactor step of Red-Green-Refactor.'
---

# Refactoring: Improving Code Without Changing Behavior

**Use this skill during the REFACTOR step of Red-Green-Refactor.** Tests must be green before refactoring.

## The Refactoring Mindset

1. **Tests are green** — Never refactor red tests
2. **Small steps** — Each change preserves behavior
3. **Commit frequently** — After each successful refactoring
4. **One smell at a time** — Don't mix refactorings
5. **Duplication is a hint, not a command** — rule of three before abstracting;
   refactor only as far as _this_ change needs (tidying the neighborhood is a
   separate session)

## Code Smell Decision Tree

### Is the code hard to understand?

| Smell                                       | Symptom                              | Reference                                         |
| ------------------------------------------- | ------------------------------------ | ------------------------------------------------- |
| [Mysterious Name](#mysterious-name)         | Name doesn't reveal intent           | [naming.md](./references/naming.md)               |
| [Long Function](#long-function)             | Function > 10-20 lines, scrolling    | [extraction.md](./references/extraction.md)       |
| [Comments explaining what](#comments)       | Comments describe mechanics, not why | [naming.md](./references/naming.md)               |
| [Primitive Obsession](#primitive-obsession) | Strings/numbers for domain concepts  | [encapsulation.md](./references/encapsulation.md) |

### Is there duplication?

| Smell                                   | Symptom                            | Reference                                         |
| --------------------------------------- | ---------------------------------- | ------------------------------------------------- |
| [Duplicated Code](#duplicated-code)     | Same code in multiple places       | [extraction.md](./references/extraction.md)       |
| [Data Clumps](#data-clumps)             | Same 3+ params appear together     | [encapsulation.md](./references/encapsulation.md) |
| [Repeated Switches](#repeated-switches) | Same switch/if-else in many places | [polymorphism.md](./references/polymorphism.md)   |

### Is the code hard to change?

| Smell                                 | Symptom                            | Reference                                         |
| ------------------------------------- | ---------------------------------- | ------------------------------------------------- |
| [Divergent Change](#divergent-change) | One class changes for many reasons | [moving.md](./references/moving.md)               |
| [Shotgun Surgery](#shotgun-surgery)   | One change touches many classes    | [moving.md](./references/moving.md)               |
| [Feature Envy](#feature-envy)         | Method uses another class's data   | [moving.md](./references/moving.md)               |
| [Message Chains](#message-chains)     | a.b().c().d() navigation chains    | [encapsulation.md](./references/encapsulation.md) |

### Is there unnecessary complexity?

| Smell                                             | Symptom                            | Reference                                           |
| ------------------------------------------------- | ---------------------------------- | --------------------------------------------------- |
| [Long Parameter List](#long-parameter-list)       | Function has > 3-4 parameters      | [api.md](./references/api.md)                       |
| [Speculative Generality](#speculative-generality) | Code for future needs not here yet | [simplification.md](./references/simplification.md) |
| [Lazy Element](#lazy-element)                     | Class/function does almost nothing | [simplification.md](./references/simplification.md) |
| [Middle Man](#middle-man)                         | Class just delegates to another    | [simplification.md](./references/simplification.md) |
| [Dead Code](#dead-code)                           | Code that's never executed         | [simplification.md](./references/simplification.md) |
| [Loops](#loops)                                   | Imperative loop obscures intent    | [data.md](./references/data.md)                     |

### Are there data problems?

| Smell                               | Symptom                          | Reference                                         |
| ----------------------------------- | -------------------------------- | ------------------------------------------------- |
| [Global Data](#global-data)         | Mutable data accessible anywhere | [encapsulation.md](./references/encapsulation.md) |
| [Mutable Data](#mutable-data)       | Data changes unexpectedly        | [data.md](./references/data.md)                   |
| [Temporary Field](#temporary-field) | Fields only used sometimes       | [encapsulation.md](./references/encapsulation.md) |

### Are there inheritance problems?

| Smell                                       | Symptom                               | Reference                                         |
| ------------------------------------------- | ------------------------------------- | ------------------------------------------------- |
| [Large Class](#large-class)                 | Class has too many responsibilities   | [inheritance.md](./references/inheritance.md)     |
| [Refused Bequest](#refused-bequest)         | Subclass ignores inherited methods    | [inheritance.md](./references/inheritance.md)     |
| [Insider Trading](#insider-trading)         | Classes share too much internal data  | [encapsulation.md](./references/encapsulation.md) |
| [Alternative Classes](#alternative-classes) | Different interfaces, similar purpose | [inheritance.md](./references/inheritance.md)     |
| [Data Class](#data-class)                   | Class only has data, no behavior      | [encapsulation.md](./references/encapsulation.md) |

## Quick Reference: Most Common Refactorings

| I want to...                    | Use this refactoring                  |
| ------------------------------- | ------------------------------------- |
| Name a complex expression       | Extract Variable                      |
| Break up a long function        | Extract Function                      |
| Remove a useless wrapper        | Inline Function                       |
| Rename for clarity              | Change Function Declaration           |
| Group related parameters        | Introduce Parameter Object            |
| Replace condition with types    | Replace Conditional with Polymorphism |
| Control access to data          | Encapsulate Variable                  |
| Move method to where data lives | Move Function                         |

## Reference Files

- **[extraction.md](./references/extraction.md)**: Extract/Inline Function, Extract/Inline Variable
- **[naming.md](./references/naming.md)**: Rename Variable/Field, Change Function Declaration
- **[encapsulation.md](./references/encapsulation.md)**: Encapsulate Variable/Collection/Record, Hide Delegate
- **[moving.md](./references/moving.md)**: Move Function/Field, Move Statements
- **[data.md](./references/data.md)**: Split Variable, Replace Derived Variable with Query
- **[api.md](./references/api.md)**: Introduce Parameter Object, Remove Flag Argument
- **[polymorphism.md](./references/polymorphism.md)**: Replace Conditional with Polymorphism
- **[simplification.md](./references/simplification.md)**: Inline Class, Remove Dead Code, Collapse Hierarchy
- **[inheritance.md](./references/inheritance.md)**: Pull Up/Push Down, Replace with Delegate

## Cross-References

- **[prefactoring](../prefactoring/SKILL.md)**: Design principles to apply BEFORE writing code
- **[pytest-unit-testing](../pytest-unit-testing/SKILL.md)**: Tests must be green before refactoring
- **[clean-architecture-validator](../clean-architecture-validator/SKILL.md)**: Layer violations to refactor
