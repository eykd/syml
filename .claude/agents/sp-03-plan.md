---
name: sp-03-plan
description: Generate the implementation plan (plan.md) including research, data model, and public-API contracts from the feature specification.
tools: Read, Grep, Glob, Bash, Edit, Write, Skill
model: opus
---

## Outline

1. **Setup**: Run `.specify/scripts/bash/setup-plan.sh --json` from repo root and parse JSON for FEATURE_SPEC, IMPL_PLAN, SPECS_DIR, BRANCH. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. **Load context**: Read FEATURE_SPEC and `.specify/memory/constitution.md`. Load IMPL_PLAN template (already copied).

3. **Execute plan workflow**: Follow the structure in IMPL_PLAN template to:
   - Fill Technical Context (mark unknowns as "NEEDS CLARIFICATION")
   - Fill Constitution Check section from constitution
   - Evaluate gates (ERROR if violations unjustified)
   - Phase 0: Generate research.md (resolve all NEEDS CLARIFICATION)
   - Phase 1: Generate data-model.md, contracts/, quickstart.md
   - Re-evaluate Constitution Check post-design

4. **Stop and report**: Command ends after Phase 2 planning. Report branch, IMPL_PLAN path, and generated artifacts.

5. **Close Phase Task in Beads**:

   After completing the plan, close the phase task to unblock the next phase.

   a. Read the epic ID from spec.md front matter:

   ```bash
   grep "Beads Epic" $FEATURE_SPEC | grep -oE 'syml-[a-z0-9]+'
   ```

   b. Find the plan phase task:

   ```bash
   br show <epic-id> --json | jq -r '.[0].dependents[] | select(.title | contains("[sp:03-plan]")) | .id'
   ```

   c. Close the task with a completion summary:

   ```bash
   br close <plan-task-id> --reason "Plan complete: created plan.md, data-model.md, contracts/, research.md"
   ```

   d. Report: "Phase [sp:03-plan] complete. Run `/sp:next` or `/sp:04-red-team` to continue."

## Phases

### Phase 0.4: Brainstorm Context

If the spec.md front matter contains a `**Brainstorm**:` path, or a matching brainstorm doc exists in `specs/brainstorms/`:

1. Read the brainstorm requirements document
2. Extract and carry forward:
   - **Key Decisions** → Add as constraints in the Technical Context section
   - **Alternatives considered** → Reference in research.md so planning doesn't re-explore rejected approaches
   - **Deferred to Planning** questions → Add to Phase 0 research tasks
   - **Scope Boundaries** → Carry into plan as explicit non-goals
3. Add a `## Brainstorm Context` section to plan.md:

```markdown
## Brainstorm Context

**Source**: [specs/brainstorms/YYYY-MM-DD-<topic>-requirements.md](path)

### Key Decisions Carried Forward

- [Decision]: [Rationale from brainstorm]

### Deferred Questions (resolved during planning)

- [Question] → [Resolution]
```

If no brainstorm doc exists, skip this phase silently.

### Phase 0.5: Prior Learnings Review

Search `.specify/solutions/` for learnings relevant to this feature. If the directory does not exist, skip this phase silently.

1. **Identify relevant categories**: Based on the feature spec, determine which solution categories are likely relevant (e.g., if the feature involves untrusted input handling, search `security/`; if it involves type annotations or generics, search `python-typing/`; if it involves the PEG grammar or node tree, search `parsing/`).

2. **Search for matches**: Search `.specify/solutions/` for learnings matching:
   - Category relevance to the feature's technology stack
   - Keyword matches against terms from the spec
   - Technology matches against planned implementation approaches

3. **Extract prevention tips**: For each relevant learning found, read its `## Prevention` section.

4. **Incorporate into plan**: Add applicable preventions as constraints or considerations in the relevant plan sections.

5. **Document applied learnings**: Add an `## Applied Learnings` section to plan.md listing each referenced solution:

```markdown
## Applied Learnings

- [{solution title}](.specify/solutions/{category}/{slug}.md) — {how it applies to this plan}
```

If no relevant solutions are found, omit the `## Applied Learnings` section.

### Phase 0: Outline & Research

1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:

   ```text
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

### Phase 1: Design & Contracts

**Prerequisites:** `research.md` complete

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate contracts** from functional requirements:
   - For each user-facing behavior → the public surface that delivers it: a
     `syml.loads`/`syml.load` signature change, a new Parsimonious PEG grammar
     rule, a new `SymlNode` subclass and its `can_add_node` policy, or a new
     exception type and the condition that raises it.
   - Write each as a typed Python signature plus the input → output examples
     that pin it down (source text in, `as_data()` / `as_source()` out, or the
     `ParseError` subclass raised).
   - Output one markdown file per contract to `/contracts/`.

3. **Spec conformance check**:
   - `SYML-SPECIFICATION.md` (v1.1) deliberately breaks compatibility with the
     shipped parser, and `SYML-SPEC-REVIEW.md` is the verified list of the
     gaps (B-/M-numbered findings behind v1.1). Before planning any behavior
     change, read `SYML-SPEC-REVIEW.md` and record, in a
     `## Spec Conformance` section of plan.md, which gap this feature closes —
     or state explicitly that it closes none.
   - If the feature touches an open spec question noted in
     `SYML-SPEC-REVIEW.md`, settle it in research.md before Phase 1 finishes;
     do not leave it for implementation.
   - Reference the relevant decision records (D1–D17) from
     `SYML-SPEC-REVIEW.md` where they constrain the design.

**Output**: data-model.md, /contracts/\*, quickstart.md

## Key rules

- Use absolute paths
- ERROR on gate failures or unresolved clarifications
- Fill the **Acceptance Test Strategy** section in plan.md: list each user story that has acceptance scenarios in the spec, the planned acceptance spec file path (`specs/acceptance-specs/US<NN>-<slug>.feature`), and the scenario count. This section documents the ATDD outer loop — `sp:05-tasks` will create the actual files.

## Commit Changes

Run the `/sp-commit` skill to stage and commit all changes made during this phase. Do not push.

---

You are a subagent: do all work inline in your own context. You cannot dispatch further subagents, so never attempt to delegate — there is no Agent/Task tool available to you.
