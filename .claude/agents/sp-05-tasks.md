---
name: sp-05-tasks
description: Generate implementation tasks organized by user story. Creates beads tasks with dependencies, skill references, and acceptance criteria. Generates pytest-bdd acceptance feature files and their unbound bindings.
tools: Read, Grep, Glob, Bash, Edit, Write, Skill
model: sonnet
---

## Outline

1. **Setup**: Run `.specify/scripts/bash/check-prerequisites.sh --json` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. **Load design documents**: Read from FEATURE_DIR:
   - **Required**: plan.md (tech stack, libraries, structure), spec.md (user stories with priorities)
   - **Optional**: data-model.md (entities), contracts/ (public signatures, grammar rules, exception types), research.md (decisions), quickstart.md (test scenarios)
   - Note: Not all projects have all documents. Generate tasks based on what's available.

3. **Retrieve Beads Epic ID**:

   a. Read the epic ID from spec.md front matter:

   ```bash
   grep "Beads Epic" FEATURE_DIR/spec.md | grep -oE 'syml-[a-z0-9]+'
   ```

   b. If not found in spec.md, search beads for epic by feature name:

   ```bash
   br list --type epic --status open --json
   ```

   - Parse JSON to find epic matching the feature branch name
   - Extract the epic ID

   c. If no epic exists, create one:

   ```bash
   br create "Feature: <feature-name>" -t epic -p 0 --description "Epic for <feature-name> feature" --json
   ```

   - Store the returned ID for use in task creation

   d. Store epic ID for subsequent task creation steps

4. **Execute task generation workflow**:
   - Load plan.md and extract tech stack, libraries, project structure, and **public-surface requirements** (grammar rules, node types and their `can_add_node` policies, `as_data()` / `as_source()` renderings, `Source`/`Pos` handling, exception types, and the public `syml.loads` / `syml.load` signatures). Also extract the `## Acceptance Test Strategy` section if present (user stories with acceptance scenarios and planned spec file paths), and the `## Spec Conformance` section if present (which `SYML-SPEC-REVIEW.md` gaps this feature closes). Map each public-surface requirement to the user story it serves.
   - Load spec.md and extract user stories with their priorities (P1, P2, P3, etc.)
   - If data-model.md exists: Extract entities and map to user stories
   - If contracts/ exists: Map each contract to the user story it serves
   - If research.md exists: Extract decisions for setup tasks
   - Generate tasks organized by user story (see Task Generation Rules below)
   - Generate dependency graph showing user story completion order
   - Create parallel execution examples per user story
   - Validate task completeness (each user story has all needed tasks, independently testable)

5. **Create Beads Tasks** (as children of the [sp:07-implement] phase task):

   **First, find the implement phase task** (created by `/sp:02-specify`):

   ```bash
   IMPLEMENT_TASK_ID=$(br show <epic-id> --json | jq -r '.[0].dependents[] | select(.title | contains("[sp:07-implement]")) | .id')
   ```

   Store this ID - all user story tasks will be created as children of this task.

   **Skill Mapping Reference** - Use these skills based on task type:

   | Task pattern                                            | Skills                                     |
   | ------------------------------------------------------- | ------------------------------------------ |
   | `Create.*entity`, `.*domain model`, `.*node type`       | `/ddd-domain-modeling`, `/pytest-unit-testing` |
   | `.*grammar.*`, `.*parser.*`, `.*visitor.*`              | `/pytest-unit-testing`, `/prefactoring`    |
   | `Write.*test`, `.*test.*`                               | `/pytest-unit-testing`                     |
   | `Write acceptance test`, `Verify acceptance`            | `/acceptance-tests`                        |
   | `Refactor.*`                                            | `/refactoring`                             |
   | `Setup.*`, `Configure.*`, `.*pyproject.*`               | (Type E, no skill)                         |
   | `.*docs.*`, `.*README.*`, `.*spec.*\.md`                | (Type D, `/glossary` for terminology)      |

   For each user story from spec.md:

   a. Create a task for the user story **as a child of the implement task** with description:

   ```bash
   br create "US<N>: <user-story-title>" -p <priority> --parent $IMPLEMENT_TASK_ID \
     --description "**Spec**: specs/$BRANCH/spec.md §US-<N>
   **Goal**: <user-story-goal-from-spec>
   **Acceptance**: <acceptance-criteria-summary>

   ## Implementation Constraints
   _(Review findings for unwritten code in this story are merged here by sp:06/08. Read this section before writing any code.)_" --json
   ```

   - `<N>`: User story number (1, 2, 3...)
   - `<priority>`: Map P1→1, P2→2, P3→3, etc.
   - `--parent $IMPLEMENT_TASK_ID`: Link to the **implement phase task** (NOT the epic)

   b. For each implementation step within the user story, create a sub-task with description:

   ```bash
   br create "<step-description>" -p <priority> --parent <user-story-task-id> \
     --description "**Spec**: specs/$BRANCH/spec.md §US-<N>, plan.md §<section>
   **Skills**: <skill-list-from-mapping>
   **Files**: <target-file-paths>
   **Acceptance**: <specific-criteria>" --json
   ```

   - `<user-story-task-id>`: The user story task ID from step (a)
   - `<skill-list-from-mapping>`: Skills from the mapping table above
   - `<target-file-paths>`: Specific files to create/modify
   - `<specific-criteria>`: Measurable acceptance criteria

   c. Establish dependencies between sequential tasks:

   ```bash
   br dep add <dependent-task-id> <blocking-task-id>
   ```

   - Add dependencies where one task must complete before another
   - Tasks marked [P] should NOT have dependencies between them (parallel execution)

   d. For parallel tasks (marked [P] in task plan):
   - Create without dependencies between them
   - They will all appear in `br ready` once their common parent is ready

6. **Generate Acceptance Feature Files** (ATDD outer loop setup):

   For each user story in spec.md that has **Acceptance Scenarios**, extract the GWT scenarios and write them as Gherkin `.feature` files in `specs/acceptance-specs/`, then bind each one with a pytest-bdd module that has **no step definitions yet**. This sets up the outer ATDD loop so ralph can run the inner TDD cycle during `sp:07-implement`.

   a. Determine the next available US number by scanning existing files:

   ```bash
   ls specs/acceptance-specs/US*.feature 2>/dev/null | sed 's/.*US0*//' | sed 's/-.*//' | sort -n | tail -1
   ```

   Start numbering from the next available number (`US00-smoke.feature` is the committed reference example, so a fresh repo starts at `US01`).

   b. For each user story, create `specs/acceptance-specs/US<NN>-<kebab-case-slug>.feature` using Gherkin:

   ```gherkin
   Feature: <user story title in sentence case>
     <one or two lines of context from the spec>

     Scenario: <scenario title in sentence case>
       Given <precondition>
       When <action>
       Then <expected outcome>
       And <additional assertion if needed>
   ```

   - File naming: `US<NN>-<kebab-case-slug>.feature` (e.g. `US03-multiline-values.feature`)
   - Each scenario gets its own `Scenario:` block under the single `Feature:` header
   - Keep scenarios behavioral (what the caller passes in and gets back), not implementation-specific
   - Extract scenarios directly from the spec's **Acceptance Scenarios** sections

   c. For each feature file, create the binding module `tests/acceptance/test_us<nn>_<slug>.py` containing **only** the marker and the `scenarios()` call — no `@given`/`@when`/`@then` definitions:

   ```python
   """Bindings for specs/acceptance-specs/US<NN>-<slug>.feature."""

   import pytest
   from pytest_bdd import scenarios

   pytestmark = pytest.mark.acceptance

   scenarios('US<NN>-<slug>.feature')
   ```

   `tests/acceptance/test_us00_smoke.py` is the shape reference — copy its layout (module docstring, `pytestmark`, `scenarios()` call) and note that the `context` fixture in `tests/acceptance/conftest.py` is what step definitions will later use to carry state between steps. The step definitions themselves are written later, by the `Write acceptance test` leaf during `sp:07-implement`.

   d. Run the acceptance suite and confirm the RED state:

   ```bash
   just acceptance 2>&1 || true
   ```

   e. Verify each new scenario fails with `StepDefinitionNotFoundError` — that is the RED marker proving the scenario is bound but not yet implemented. A scenario that errors any other way (a collection error, a missing feature file, a malformed `Feature:` header) is a setup bug: fix it before moving on.

   f. Record the feature file and binding module paths in the report for reference.

   **Important**: The feature files and their bindings must exist BEFORE ralph processes `US<N>` tasks, because ralph's ATDD cycle requires them. If spec.md has no acceptance scenarios for a user story, skip that story (no feature file needed).

7. **Verify Task Hierarchy**:

   ```bash
   br dep tree <epic-id> --direction up
   ```

   - Note: `--direction up` shows dependents/children (default `down` shows blockers, which is empty for an epic)
   - Verify the hierarchy: Epic → User Story Tasks → Implementation Sub-tasks
   - Check for any circular dependencies: `br dep cycles`

8. **Close Phase Task in Beads**:

   After creating all implementation tasks, close the 05-tasks phase task to unblock the implement phase.

   a. Find the tasks phase task:

   ```bash
   br show <epic-id> --json | jq -r '.[0].dependents[] | select(.title | contains("[sp:05-tasks]") and .status == "open") | .id'
   ```

   b. Close the task with a completion summary:

   ```bash
   br close <tasks-task-id> --reason "Created <N> tasks across <M> user stories under [sp:07-implement]"
   ```

   c. The [sp:06-analyze] phase task is now ready (its dependency on 05-tasks is satisfied).

   d. Report: "Phase [sp:05-tasks] complete. Run `/sp:next` or `/sp:06-analyze` to validate artifacts."

9. **Report**: Output summary including:
   - **Beads epic ID** and total tasks created in beads
   - **Implement task ID** (`$IMPLEMENT_TASK_ID`) containing all user story tasks
   - Task count per user story (with task IDs)
   - **Acceptance feature files** created in `specs/acceptance-specs/` and their bindings in `tests/acceptance/` (with file paths)
   - **RED state confirmed**: every new scenario fails with `StepDefinitionNotFoundError`
   - Parallel opportunities identified
   - Independent test criteria for each story
   - Suggested MVP scope (typically just User Story 1)
   - **Next step**: Run `/sp:next` or `/sp:06-analyze` to validate cross-artifact consistency
   - **How to view ready tasks**: `br ready --json`

The tasks should be immediately executable via beads - each task must be specific enough that an LLM can complete it without additional context.

## Task Generation Rules

**CRITICAL**: Tasks MUST be organized by user story to enable independent implementation and testing.

**CRITICAL**: Task descriptions are the ONLY context ralph passes to claude. They must be fully self-contained — a fresh claude session must be able to implement the task without exploring the codebase from scratch.

### Task Type Classification

Classify each piece of work per `/beads-task-chains` taxonomy (Types A-E) and apply the corresponding chain pattern. Quick reference:

- **Type A: Testable code** — full ATDD + TDD chain (acceptance → red → green → refactor → ... → verify)
- **Type B: Static pages** — build + visual verify
- **Type C: Design & style** — build + visual verify
- **Type D: Documentation** — write + lint
- **Type E: Configuration** — change + validate

See `/beads-task-chains` for full chain construction patterns and `references/description-templates.md` for parameterized task description templates.

### Behavior Decomposition (for Type A tasks)

Read plan.md + spec.md at task generation time to identify behaviors:

- Each node type / data model = 1 behavior
- Each grammar rule or visitor method = 1 behavior
- Each public API surface (`loads`, `load`, `as_data`, `as_source`) change = 1 behavior
- Each error path (a new `ParseError` subclass or raise condition) = 1 behavior
- Each cross-cutting concern = 1 behavior

### Dependency Chain Construction

Construct chains per `/beads-task-chains` patterns. For Type A (testable code), use the full ATDD/TDD chain. For Types B-E, use the corresponding lightweight pattern.

### Task Description Templates

Use templates from `/beads-task-chains` — see `references/description-templates.md` for all parameterized templates (WRITE_ACCEPTANCE_TEST, RED, GREEN, REFACTOR, VERIFY_ACCEPTANCE, STATIC_PAGE, DESIGN_STYLE, DOCUMENTATION, CONFIGURATION).

### Beads Task Format

Use the naming convention from `/beads-task-chains` (US tasks, ATDD sub-tasks, TDD sub-tasks).

### Priority Mapping

| Spec Priority | Beads Priority | Description             |
| ------------- | -------------- | ----------------------- |
| Epic          | 0              | Feature-level (highest) |
| P1            | 1              | Critical user story     |
| P2            | 2              | High priority           |
| P3            | 3              | Medium priority         |
| P4+           | 4+             | Lower priority          |

### Dependency Rules

1. **Sequential tasks**: Use `br dep add <child> <parent>` to create blocking relationships
2. **Parallel tasks**: Do NOT add dependencies between them - they'll appear together in `br ready`
3. **Cross-story dependencies**: Minimize these; each story should be independently completable
4. **Setup/Foundational**: These block all user story tasks
5. **ATDD/TDD chains**: Each step blocks the next in sequence (acceptance → red → green → refactor → ... → verify)

### Task Organization

1. **From User Stories (spec.md)** - PRIMARY ORGANIZATION:
   - Each user story (P1, P2, P3...) becomes a beads task under the implement phase task
   - Classify each story's work by task type (A through E)
   - For Type A: Generate full ATDD/TDD dependency chain
   - For Types B-E: Generate appropriate task chain per type
   - Map all related components to their story:
     - Models needed for that story
     - Services needed for that story
     - Public API surfaces needed for that story (from contracts/)
     - Grammar rules, node types, and visitor methods needed for that story (from plan.md)
   - Mark story dependencies (most stories should be independent)

2. **From Contracts**:
   - Map each contract (public signature, grammar rule, node policy, exception) → to the user story it serves
   - Each contract becomes a behavior in the Type A ATDD/TDD chain

3. **From Data Model**:
   - Map each entity to the user story(ies) that need it
   - If entity serves multiple stories: Put in earliest story or Setup phase
   - Each entity becomes a behavior in the Type A ATDD/TDD chain

4. **From Setup/Infrastructure**:
   - Shared infrastructure → Setup phase tasks (Type E)
   - Foundational/blocking tasks → Foundational phase tasks
   - Story-specific setup → within that story's sub-tasks

5. **From Plan (Docs & Spec Conformance)**:
   - Scan plan.md for documentation and spec-conformance work
   - Map each `SYML-SPEC-REVIEW.md` gap this feature closes to the user story that closes it
   - Classify docs work (README, `SYML-SPECIFICATION.md`, decision records) as Type D
   - Classify tooling and config work (pyproject, pre-commit, `just` recipes) as Type E

### Phase Structure

- **Phase 1**: Setup (project initialization) - Type E tasks directly under implement task
- **Phase 2**: Foundational (blocking prerequisites) - Type E tasks directly under implement task
- **Phase 3+**: User Stories in priority order (P1, P2, P3...)
  - Each user story is a task under the implement task
  - Type A stories get full ATDD/TDD chain as sub-tasks
  - Type B/C/D/E stories get appropriate task chains
  - Each phase should be a complete, independently testable increment
- **Final Phase**: Polish & Cross-Cutting Concerns
  - Documentation update task if the feature changes public behavior or closes a `SYML-SPEC-REVIEW.md` gap
  - This task depends on ALL user story sub-tasks completing first

## Beads Error Handling

If beads commands fail during task creation:

1. **Epic not found**: Create a new epic for the feature
2. **Task creation fails**: Log error, continue with remaining tasks, report failures at end
3. **Dependency cycle detected**: Remove the problematic dependency, log warning
4. **DB corruption** (`UNIQUE constraint failed: blocked_issues_cache.issue_id`, `database disk image is malformed`, `ISSUE_NOT_FOUND` for a task that just existed): First check `br --version` is `>= 0.5.5`. Older builds had a cross-process WAL checkpoint race (beads_rust#457) that silently dropped issues and dependency edges under concurrent use; it was fixed engine-side in 0.5.5, not by retrying. On a current build, run `br doctor --repair` once; if `br doctor` still reports `integrity_check` or `SCHEMA_MISMATCH`, rebuild from the committed JSONL: `rm .beads/beads.db*; br sync --import-only --rebuild` (see `/install-br`).
5. **br command not found**: Suggest installing br via curl

If beads commands fail completely, report failures and suggest troubleshooting steps.

## Commit Changes

Run the `/sp-commit` skill to stage and commit all changes made during this phase. Do not push.

---

You are a subagent: do all work inline in your own context. You cannot dispatch further subagents, so never attempt to delegate — there is no Agent/Task tool available to you.
