# Brainstorm a Feature or Improvement

Brainstorming helps answer **WHAT** to build through collaborative dialogue. It precedes `/sp:02-specify`, which converges the brainstorm output into a formal specification with branch, beads epic, and dependency chain.

The durable output of this workflow is a **requirements document** in `specs/brainstorms/`. It captures product decisions, scope boundaries, and success criteria so that `/sp:02-specify` can focus on convergent specification rather than divergent exploration.

This skill does not implement code, create branches, or set up beads. It explores, clarifies, and documents decisions for later specification.

**IMPORTANT**: `/sp:02-specify` is always the mandatory next step after brainstorming. Brainstorm never bypasses specify.

## Core Principles

1. **Assess scope first** - Match the amount of ceremony to the size and ambiguity of the work.
2. **Be a thinking partner** - Suggest alternatives, challenge assumptions, and explore what-ifs instead of only extracting requirements.
3. **Resolve product decisions here** - User-facing behavior, scope boundaries, and success criteria belong in this workflow. Detailed implementation belongs in planning.
4. **Keep implementation out of the requirements doc by default** - Do not include libraries, schemas, endpoints, file layouts, or code-level design unless the brainstorm itself is inherently about a technical or architectural change.
5. **Right-size the artifact** - Simple work gets a compact requirements document. Larger work gets a fuller document. Do not add ceremony that does not help specification.
6. **Apply YAGNI to carrying cost, not coding effort** - Prefer the simplest approach that delivers meaningful value. Avoid speculative complexity and hypothetical future-proofing, but low-cost polish or delight is worth including when its ongoing cost is small and easy to maintain.

## Interaction Rules

1. **Ask one question at a time** - Do not batch several unrelated questions into one message.
2. **Use `AskUserQuestion` tool** - Always use the platform's blocking question tool for questions.
3. **Prefer single-select multiple choice** - Use single-select when choosing one direction, one priority, or one next step.
4. **Use multi-select rarely and intentionally** - Use it only for compatible sets such as goals, constraints, non-goals, or success criteria that can all coexist. If prioritization matters, follow up by asking which selected item is primary.

## Output Guidance

- **Keep outputs concise** - Prefer short sections, brief bullets, and only enough detail to support the next decision.

## Feature Description

<feature_description> $ARGUMENTS </feature_description>

**If the feature description above is empty, ask the user:** "What would you like to explore? Please describe the feature, problem, or improvement you're thinking about."

Do not proceed until you have a feature description from the user.

## Execution Flow

### Phase 0: Resume, Assess, and Route

#### 0.1 Resume Existing Work When Appropriate

If the user references an existing brainstorm topic, or there is an obvious recent matching `*-requirements.md` file in `specs/brainstorms/`:

- Read the document
- Confirm with the user before resuming: "Found an existing requirements doc for [topic]. Should I continue from this, or start fresh?"
- If resuming, summarize the current state briefly, continue from its existing decisions and outstanding questions, and update the existing document instead of creating a duplicate

#### 0.2 Assess Whether Full Brainstorming Is Needed

**Clear requirements indicators:**

- Specific acceptance criteria provided
- Referenced existing patterns to follow
- Described exact expected behavior
- Constrained, well-defined scope

**If requirements are already clear:**
Keep the interaction brief. Confirm understanding and skip to Phase 3 to write a compact requirements doc. sp:02-specify is still the mandatory next step.

#### 0.3 Assess Scope

Use the feature description plus a light repo scan to classify the work:

- **Lightweight** - small, well-bounded, low ambiguity
- **Standard** - normal feature or bounded refactor with some decisions to make
- **Deep** - cross-cutting, strategic, or highly ambiguous

If the scope is unclear, ask one targeted question to disambiguate and then proceed.

### Phase 1: Understand the Idea

#### 1.1 Existing Context Scan

Scan the repo before substantive brainstorming. Match depth to scope:

**Lightweight** - Search for the topic, check if something similar already exists, and move on.

**Standard and Deep** - Two passes:

_Constraint Check_ - Check `CLAUDE.md` and `.specify/memory/constitution.md` (if it exists) for workflow, product, or scope constraints that affect the brainstorm. If these add nothing, move on.

_Topic Scan_ - Search for relevant terms in existing specs, features, and patterns. Read the most relevant existing artifact if one exists. Skim adjacent examples covering similar behavior.

If nothing obvious appears after a short scan, say so and continue. Do not drift into technical planning - avoid inspecting tests, migrations, deployment, or low-level architecture unless the brainstorm is itself about a technical decision.

#### 1.2 Product Pressure Test

Before generating approaches, challenge the request to catch misframing. Match depth to scope:

**Lightweight:**

- Is this solving the real user problem?
- Are we duplicating something that already covers this?
- Is there a clearly better framing with near-zero extra cost?

**Standard:**

- Is this the right problem, or a proxy for a more important one?
- What user or business outcome actually matters here?
- What happens if we do nothing?
- Is there a nearby framing that creates more user value without more carrying cost? If so, what complexity does it add?
- Given the current project state, user goal, and constraints, what is the single highest-leverage move right now: the request as framed, a reframing, one adjacent addition, a simplification, or doing nothing?
- Favor moves that compound value, reduce future carrying cost, or make the product meaningfully more useful or compelling
- Use the result to sharpen the conversation, not to bulldoze the user's intent

**Deep** - Standard questions plus:

- What durable capability should this create in 6-12 months?
- Does this move the product toward that, or is it only a local patch?

#### 1.3 Collaborative Dialogue

**Guidelines:**

- Ask questions **one at a time** using `AskUserQuestion`
- Prefer multiple choice when natural options exist
- Prefer **single-select** when choosing one direction, one priority, or one next step
- Use **multi-select** only for compatible sets that can all coexist; if prioritization matters, ask which selected item is primary
- Start broad (problem, users, value) then narrow (constraints, exclusions, edge cases)
- Clarify the problem frame, validate assumptions, and ask about success criteria
- Make requirements concrete enough that specification will not need to invent behavior
- Surface dependencies or prerequisites only when they materially affect scope
- Resolve product decisions here; leave technical implementation choices for planning
- Bring ideas, alternatives, and challenges instead of only interviewing

**Exit condition:** Continue until the idea is clear OR the user explicitly wants to proceed.

### Phase 2: Explore Approaches

If multiple plausible directions remain, propose **2-3 concrete approaches** based on research and conversation. Otherwise state the recommended direction directly.

When useful, include one deliberately higher-upside alternative:

- Identify what adjacent addition or reframing would most increase usefulness, compounding value, or durability without disproportionate carrying cost. Present it as a challenger option alongside the baseline, not as the default. Omit it when the work is already obviously over-scoped or the baseline request is clearly the right move.

For each approach, provide:

- Brief description (2-3 sentences)
- Pros and cons
- Key risks or unknowns
- When it's best suited

Lead with your recommendation and explain why. Prefer simpler solutions when added complexity creates real carrying cost, but do not reject low-cost, high-value polish just because it is not strictly necessary.

If one approach is clearly best and alternatives are not meaningful, skip the menu and state the recommendation directly.

If relevant, call out whether the choice is:

- Reuse an existing pattern
- Extend an existing capability
- Build something net new

### Phase 3: Capture the Requirements

Write or update a requirements document only when the conversation produced durable decisions worth preserving.

This document should behave like a lightweight PRD without PRD ceremony. Include what specification needs to converge well, and skip sections that add no value for the scope.

The requirements document is for product definition and scope control. Do **not** include implementation details such as libraries, schemas, endpoints, file layouts, or code structure unless the brainstorm is inherently technical and those details are themselves the subject of the decision.

**Required content for non-trivial work:**

- Problem frame
- Concrete requirements or intended behavior with stable IDs
- Scope boundaries
- Success criteria

**Include when materially useful:**

- Key decisions and rationale
- Dependencies or assumptions
- Outstanding questions
- Alternatives considered
- High-level technical direction only when the work is inherently technical and the direction is part of the product/architecture decision

**Document structure:** Use this template and omit clearly inapplicable optional sections:

```markdown
---
date: YYYY-MM-DD
topic: <kebab-case-topic>
---

# <Topic Title>

## Problem Frame

[Who is affected, what is changing, and why it matters]

## Requirements

**[Group Header]**

- R1. [Concrete requirement in this group]
- R2. [Concrete requirement in this group]

**[Group Header]**

- R3. [Concrete requirement in this group]

## Success Criteria

- [How we will know this solved the right problem]

## Scope Boundaries

- [Deliberate non-goal or exclusion]

## Key Decisions

- [Decision]: [Rationale]

## Dependencies / Assumptions

- [Only include if material]

## Outstanding Questions

### Resolve Before Specify

- [Affects R1][User decision] [Question that must be answered before specification can proceed]

### Deferred to Planning

- [Affects R2][Technical] [Question that should be answered during planning or codebase exploration]
- [Affects R2][Needs research] [Question that likely requires research during planning]

## Next Steps

[Always: `-> /sp:02-specify` to create the formal specification]
[If `Resolve Before Specify` is not empty: `-> Resume /sp:01-brainstorm` to resolve blocking questions first]
```

**Visual communication** - Include a visual aid when the requirements would be significantly easier to understand with one:

| Requirements describe...                                                       | Visual aid                                          | Placement                                                                                      |
| ------------------------------------------------------------------------------ | --------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| A multi-step user workflow or process                                          | Mermaid flow diagram or ASCII flow with annotations | After Problem Frame, or under its own `## User Flow` heading for substantial flows (>10 nodes) |
| 3+ behavioral modes, variants, or states                                       | Markdown comparison table                           | Within the Requirements section                                                                |
| 3+ interacting participants (user roles, system components, external services) | Mermaid or ASCII relationship diagram               | After Problem Frame, or under its own `## Architecture` heading                                |
| Multiple competing approaches being compared                                   | Comparison table                                    | Within Phase 2 approach exploration                                                            |

**When to skip visual aids:**

- Prose already communicates the concept clearly
- The diagram would just restate the requirements in visual form without adding comprehension value
- The visual describes implementation architecture, data schemas, state machines, or code structure (that belongs in planning)
- The brainstorm is simple and linear

**Format selection:**

- **Mermaid** (default) for simple flows - 5-15 nodes, standard flowchart shapes. Use `TB` direction.
- **ASCII/box-drawing diagrams** for annotated flows that need rich in-box content. Follow 80-column max.
- **Markdown tables** for mode/variant comparisons and approach comparisons.
- Prose is authoritative: when a visual aid and surrounding prose disagree, the prose governs.

For **Standard** and **Deep** brainstorms, a requirements document is usually warranted.

For **Lightweight** brainstorms, keep the document compact. Skip document creation when the user only needs brief alignment and no durable decisions need to be preserved.

For very small requirements docs with only 1-3 simple requirements, plain bullet requirements are acceptable. For **Standard** and **Deep** requirements docs, use stable IDs like `R1`, `R2`, `R3` so specification and later review can refer to them unambiguously.

When requirements span multiple distinct concerns, group them under bold topic headers within the Requirements section. Group by logical theme, not by the order they were discussed. Requirements keep their original stable IDs - numbering does not restart per group.

Before finalizing, check:

- What would `sp:02-specify` still have to invent if this brainstorm ended now?
- Do any requirements depend on something claimed to be out of scope?
- Are any unresolved items actually product decisions rather than planning questions?
- Did implementation details leak in when they shouldn't have?
- Is there a low-cost change that would make this materially more useful?
- Would a visual aid help a reader grasp the requirements faster than prose alone?

If specification would need to invent product behavior, scope boundaries, or success criteria, the brainstorm is not complete yet.

Ensure `specs/brainstorms/` directory exists before writing.

If a document contains outstanding questions:

- Use `Resolve Before Specify` only for questions that truly block specification
- If `Resolve Before Specify` is non-empty, keep working those questions during the brainstorm by default
- If the user explicitly wants to proceed anyway, convert each remaining item into an explicit decision, assumption, or `Deferred to Planning` question before proceeding
- Do not force resolution of technical questions during brainstorming just to remove uncertainty
- Put technical questions, or questions that require validation or research, under `Deferred to Planning` when they are better answered there
- Use tags like `[Needs research]` when the planner should likely investigate the question rather than answer it from repo context alone
- Carry deferred questions forward explicitly rather than treating them as a failure to finish the requirements doc

### Phase 4: Handoff

**sp:02-specify is always the mandatory next step.** Brainstorm produces a requirements doc, not a spec. The formal specification (with branch, beads epic, and dependency chain) is always created by sp:02-specify.

#### 4.1 Present Next-Step Options

Present next steps using `AskUserQuestion`.

If `Resolve Before Specify` contains any items:

- Ask the blocking questions now, one at a time, by default
- If the user explicitly wants to proceed anyway, first convert each remaining item into an explicit decision, assumption, or `Deferred to Planning` question
- If the user chooses to pause instead, present the handoff as paused rather than complete
- Do not offer `Proceed to sp:02-specify` while `Resolve Before Specify` remains non-empty

**Options when no blocking questions remain:**

- **Proceed to sp:02-specify (Recommended)** - Create the formal specification from this brainstorm
- **Ask more questions** - Continue clarifying scope, preferences, or edge cases
- **Done for now** - Return later

Never offer "proceed directly to work", "skip to planning", or any option that bypasses sp:02-specify.

#### 4.2 Handle the Selected Option

**If user selects "Proceed to sp:02-specify":**

Display the closing summary and instruct the user to run `/sp:02-specify` with context from the brainstorm. Include the brainstorm doc path so specify can discover it.

**If user selects "Ask more questions":** Return to Phase 1.3 (Collaborative Dialogue) and continue. Do not show the closing summary yet.

**If user selects "Done for now":** Display the paused summary.

#### 4.3 Closing Summary

**When complete and ready for specification:**

```text
Brainstorm complete!

Requirements doc: specs/brainstorms/YYYY-MM-DD-<topic>-requirements.md

Key decisions:
- [Decision 1]
- [Decision 2]

Next step: /sp:02-specify <topic description>
```

**When paused with blocking questions:**

```text
Brainstorm paused.

Requirements doc: specs/brainstorms/YYYY-MM-DD-<topic>-requirements.md

Specification is blocked by:
- [Blocking question 1]
- [Blocking question 2]

Resume with /sp:01-brainstorm to resolve these before specification.
```

---

**Subagent policy:** The interview MUST run in the main context — never delegate user interaction to a subagent. Use Explore subagents for non-interactive codebase research (e.g. scanning existing code, reading specs, checking glossary).
