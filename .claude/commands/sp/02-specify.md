## Outline

## Interview Protocol (One Question at a Time)

This command is **explicitly interactive**.

- **Always use the `AskUserQuestion` tool** to ask clarification questions — never render questions as Markdown tables or ask the user to "reply with a letter." The command runs in the main context, where `AskUserQuestion` is available. Asking inline as plain text is a bug, not the intended behavior.
- Ask **one question at a time** with `AskUserQuestion` and wait for the answer before deciding the next question — later questions often depend on earlier answers. Because `AskUserQuestion` blocks for the answer within this run, you do **not** stop and wait for a re-invocation; keep the interview going until you are confident or the user signals completion.
- **Fallback only:** If `AskUserQuestion` is genuinely unavailable, or a spec already exists with `[NEEDS CLARIFICATION]` markers / an open interview question, treat the user input provided above as the answer to the **most recently asked** question (unless the input is empty).
- Keep interview answers in working memory during the session; persist them into the spec when writing it.
- The interview ends only when you are **95% confident** you understand the requirements across all taxonomy categories (see Step 5), or the user signals completion ("done", "skip", "that's enough").

After the interview is complete and the spec is written, proceed to (or hand off into) `/sp:03-plan`.

## Glossary Terms Discovery

During the interview, identify any new domain terms introduced by the user:

1. **For each potential domain term** (nouns, verbs describing business concepts):
   - Check if term exists in `docs/glossary.md`
   - If new term: Ask a clarifying question about its meaning **via `AskUserQuestion`** (e.g., "I notice you're using the term 'campaign'. Can you clarify what that means in your domain?")
   - Add to glossary with user-provided definition

2. **Use `/glossary` skill to**:
   - Validate terminology consistency in spec
   - Identify synonyms that need consolidation
   - Ensure all domain concepts are captured

This ensures Ubiquitous Language is established during specification phase.

The text the user typed after `/sp:02-specify` in the triggering message **is** the feature description. Assume you always have it available in this conversation even if the input appears literally below. Do not ask the user to repeat it unless they provided an empty command.

## Feature Description

<feature_description> $ARGUMENTS </feature_description>

Given that feature description, do this:

1. **Initialize Beads (if needed)**:

   a. Check if beads is already initialized:

   ```bash
   test -d .beads && echo "initialized" || echo "not_initialized"
   ```

   b. If not initialized, initialize beads:

   ```bash
   br init
   ```

   - This creates the `.beads/` directory for git-backed task tracking
   - If initialization fails, display error and suggest installing br via curl first

   c. Verify initialization succeeded:

   ```bash
   test -d .beads && echo "beads ready" || echo "ERROR: beads initialization failed"
   ```

2. **Generate a concise short name** (2-4 words) for the branch:
   - Analyze the feature description and extract the most meaningful keywords
   - Create a 2-4 word short name that captures the essence of the feature
   - Use action-noun format when possible (e.g., "add-user-auth", "fix-payment-bug")
   - Preserve technical terms and acronyms (OAuth2, API, JWT, etc.)
   - Keep it concise but descriptive enough to understand the feature at a glance
   - Examples:
     - "I want to add user authentication" → "user-auth"
     - "Implement OAuth2 integration for the API" → "oauth2-api-integration"
     - "Create a dashboard for analytics" → "analytics-dashboard"
     - "Fix payment processing timeout bug" → "fix-payment-timeout"

3. **Run the feature creation script**:

   Run the script with the generated short-name, allowing it to auto-detect the next available number:

   ```bash
   .specify/scripts/bash/create-new-feature.sh --json --short-name "<short-name-from-step-2>" "<feature-description>"
   ```

   **How it works**:
   - The script will automatically:
     - Fetch all remote branches (`git fetch --all --prune`)
     - Find the highest number across ALL branches and specs (not filtered by name)
     - Assign the next sequential number (e.g., if 010 exists, use 011)
     - Create the branch and spec directory
   - Replace `<short-name-from-step-2>` with the short name generated in step 2
   - For single quotes in args like "I'm Groot", use escape syntax: `'I'\''m Groot'` (or use double-quotes: `"I'm Groot"`)
   - The script outputs JSON with `BRANCH_NAME` and `SPEC_FILE` paths

   **IMPORTANT**:
   - You must only ever run this script once per feature
   - The JSON is provided in the terminal as output - always refer to it to get the actual content you're looking for
   - Do NOT pass `--number` manually - let the script auto-detect to avoid duplicate numbering

4. **Load Brainstorm Context (if available)**:

   Search `specs/brainstorms/` for requirements documents that match the feature description keywords.

   ```bash
   ls specs/brainstorms/*.md 2>/dev/null | head -10
   ```

   a. If matching brainstorm doc(s) found, confirm with the user **via `AskUserQuestion`**: "Found brainstorm doc at `<path>`. Use this as input for specification?" (offer Yes / No options).

   b. If confirmed, read the brainstorm requirements doc and use it to accelerate the interview:
   - Pre-populate interview answers from the brainstorm's Requirements, Key Decisions, and Scope Boundaries
   - Mark taxonomy categories as "Clear" where the brainstorm already covers them
   - Skip interview questions already answered in the brainstorm
   - Carry forward Outstanding Questions:
     - "Resolve Before Specify" items become interview questions (ask them during Step 6)
     - "Deferred to Planning" items are preserved in the spec's Assumptions section for sp:03-plan
   - Reference the brainstorm doc path in the spec front matter: `**Brainstorm**: specs/brainstorms/<filename>`

   c. If no brainstorm found or user declines, proceed with current flow unchanged.

5. Load `.specify/templates/spec-template.md` to understand required sections.

6. **Pre-Spec Clarification Interview**:

   Before writing the spec, conduct a structured interview to resolve ambiguities in the feature description. This ensures the spec is written with full understanding of the user's intent.

   **Note**: If a brainstorm doc was loaded in Step 4, categories already covered by the brainstorm should be marked "Clear" and their questions skipped. Focus the interview on gaps the brainstorm did not address.

   a. **Ambiguity & Coverage Scan**: Analyze the feature description (and brainstorm doc if loaded) using this taxonomy. For each category, assess status: Clear / Partial / Missing.

   **Functional Scope & Behavior**:
   - Core user goals & success criteria
   - Explicit out-of-scope declarations
   - User roles / personas differentiation

   **Domain & Data Model**:
   - Entities, attributes, relationships
   - Identity & uniqueness rules
   - Lifecycle/state transitions
   - Data volume / scale assumptions

   **Interaction & UX Flow**:
   - Critical user journeys / sequences
   - Error/empty/loading states
   - Accessibility or localization notes

   **Non-Functional Quality Attributes**:
   - Performance (latency, throughput targets)
   - Scalability (horizontal/vertical, limits)
   - Reliability & availability (uptime, recovery expectations)
   - Observability (logging, metrics, tracing signals)
   - Security & privacy (authN/Z, data protection, threat assumptions)
   - Compliance / regulatory constraints (if any)

   **Integration & External Dependencies**:
   - External services/APIs and failure modes
   - Data import/export formats
   - Protocol/versioning assumptions

   **Edge Cases & Failure Handling**:
   - Negative scenarios
   - Rate limiting / throttling
   - Conflict resolution (e.g., concurrent edits)

   **Constraints & Tradeoffs**:
   - Technical constraints (language, storage, hosting)
   - Explicit tradeoffs or rejected alternatives

   **Terminology & Consistency**:
   - Canonical glossary terms
   - Avoided synonyms / deprecated terms

   For each category with Partial or Missing status, generate a candidate question unless:
   - A reasonable default exists (see defaults list below)
   - The information is better deferred to planning phase
   - Clarification would not materially change implementation or validation strategy

   b. **Prioritize Questions**: Rank by (Impact x Uncertainty). Prioritize: scope > security/privacy > user experience > technical details. Ensure category coverage balance — avoid asking two low-impact questions when a single high-impact area is unresolved.

   c. **Interactive Questioning Loop** (one question at a time, no cap):

   Keep asking questions **with the `AskUserQuestion` tool** until **95% confident** you understand the desired requirements. Stop when:
   - All taxonomy categories are Clear or have reasonable defaults
   - User signals completion ("done", "skip", "that's enough")

   **Every question is asked via `AskUserQuestion`** — do not print Markdown tables or free-text "reply with a letter" prompts. The tool renders the options as a selectable list and always offers an "Other" free-form entry, so you do not need to add a manual "short answer" option.

   For **multiple-choice** questions:
   - Analyze all options and determine the **most suitable option** based on best practices, common patterns, risk reduction, and alignment with project goals
   - Build the `AskUserQuestion` call with that option **first** and `(Recommended)` appended to its label; use each option's `description` to explain the trade-off and reasoning
   - Provide 2–4 options; the tool's automatic "Other" choice covers any free-form alternative
   - Use single-select by default; only set `multiSelect: true` for compatible sets that can coexist (e.g. goals, constraints, non-goals)

   For **short-answer** questions (no meaningful discrete options):
   - Still use `AskUserQuestion`. Offer your suggested answer as the first option labeled `(Recommended)`, plus any plausible alternatives; the user can pick the suggestion or type their own via "Other"

   After the user answers:
   - The tool returns the selected option (or the user's "Other" text) directly — use it
   - If a free-form answer is ambiguous, ask a quick follow-up `AskUserQuestion` to disambiguate (does not count as a new question)

   d. **If no meaningful ambiguities detected**: Skip the interview entirely with a note: "No critical ambiguities detected. Proceeding to write specification."

   e. **Glossary discovery** happens during the interview — see Glossary Terms Discovery section above.

7. Follow this execution flow to write the spec, **incorporating all interview answers**:
   1. Parse user description from Input
      If empty: ERROR "No feature description provided"
   2. Extract key concepts from description + interview answers
      Identify: actors, actions, data, constraints
   3. For any remaining unclear aspects (should be rare after the interview):
      - Make informed guesses based on context and industry standards
      - Mark with [NEEDS CLARIFICATION: specific question] only if:
        - The choice significantly impacts feature scope or user experience
        - Multiple reasonable interpretations exist with different implications
        - No reasonable default exists
      - Prioritize clarifications by impact: scope > security/privacy > user experience > technical details
   4. Fill User Scenarios & Testing section
      If no clear user flow: ERROR "Cannot determine user scenarios"
   5. Generate Functional Requirements
      Each requirement must be testable
      Use reasonable defaults for unspecified details (document assumptions in Assumptions section)
   6. Define Success Criteria
      Create measurable, technology-agnostic outcomes
      Include both quantitative metrics (time, performance, volume) and qualitative measures (user satisfaction, task completion)
      Each criterion must be verifiable without implementation details
   7. Identify Key Entities (if data involved)
   8. Add a `## Clarifications` section documenting Q/A pairs from the interview:
      - Under a `### Session YYYY-MM-DD` subheading
      - Format: `- Q: <question> → A: <final answer>`
   9. Return: SUCCESS (spec ready for planning)

8. Write the specification to SPEC_FILE using the template structure, replacing placeholders with concrete details derived from the feature description and interview answers, while preserving section order and headings.

9. **Create Beads Epic for Feature**:

   a. Check if an epic already exists for this feature branch:

   ```bash
   br list --type epic --status open --json 2>/dev/null | grep -i "<feature-name>" || echo "no_existing_epic"
   ```

   b. If no existing epic, create one:

   ```bash
   br create "Feature: <feature-name>" -t epic -p 0 --description "Spec: specs/<branch>/spec.md" --json
   ```

   - `<feature-name>`: The short name generated in step 2
   - `<branch>`: The BRANCH_NAME from step 3
   - Priority 0 = highest (epic level)
   - Type = epic

   c. Parse the epic ID from the JSON response (format: `syml-xxxx`)

   d. If epic already exists, retrieve its ID:

   ```bash
   br list --type epic --status open --json | jq -r '.issues[] | select(.title | contains("<feature-name>")) | .id'
   ```

   e. **Store epic ID in spec.md**: Add the epic ID to the spec.md front matter:

   ```markdown
   **Feature Branch**: `<branch>`
   **Created**: <date>
   **Status**: Draft
   **Beads Epic**: `<epic-id>`
   ```

   f. If epic creation fails, display error but continue with spec creation (beads integration is enhancement, not blocker)

10. **Create Phase Tasks with Dependency Chain**:

After creating the epic, create ALL phase tasks upfront with dependencies. This enables `/sp:next` to orchestrate the workflow.

a. Create all phase tasks under the epic with structured descriptions:

```bash
# Extract feature name from branch (e.g., "010-user-auth" -> "user-auth")
FEATURE_NAME="<short-name-from-step-2>"
BRANCH="<branch-name-from-step-3>"

# Create phase tasks (store IDs from JSON responses)
br create "[sp:03-plan] Create implementation plan for $FEATURE_NAME" -p 1 --parent <epic-id> \
  --description "**Spec**: specs/$BRANCH/spec.md
**Skills**: /prefactoring, /latent-features, /glossary
**Context**: Generate plan.md with technical architecture, data-model.md if needed
**Acceptance**: All technical decisions documented, file structure defined" --json
# Store returned ID as PLAN_ID

br create "[sp:04-red-team] Perform adversarial review for $FEATURE_NAME" -p 2 --parent <epic-id> \
  --description "**Spec**: specs/$BRANCH/spec.md, plan.md
**Skills**: None
**Context**: Adversarial review of spec and plan; enhance plan.md with security, edge cases, performance, accessibility
**Acceptance**: plan.md enhanced with adversarial findings; red team review complete" --json
# Store returned ID as RED_TEAM_ID

br create "[sp:05-tasks] Generate implementation tasks for $FEATURE_NAME" -p 1 --parent <epic-id> \
  --description "**Spec**: specs/$BRANCH/spec.md, plan.md
**Skills**: /prefactoring, /glossary
**Context**: Create beads tasks with skill references and acceptance criteria
**Acceptance**: All user stories have beads tasks with descriptions" --json
# Store returned ID as TASKS_ID

br create "[sp:06-analyze] Analyze artifacts for $FEATURE_NAME" -p 2 --parent <epic-id> \
  --description "**Spec**: specs/$BRANCH/spec.md, plan.md, beads tasks
**Skills**: None (read-only analysis)
**Context**: Validate cross-artifact consistency, coverage gaps, constitution alignment
**Acceptance**: No CRITICAL issues; coverage report shows all requirements mapped" --json
# Store returned ID as ANALYZE_ID

br create "[sp:07-implement] Execute implementation for $FEATURE_NAME" -p 1 --parent <epic-id> \
  --description "**Spec**: specs/$BRANCH/spec.md, plan.md
**Skills**: Per-task (see task descriptions)
**Context**: TDD implementation - strict red-green-refactor for all tasks
**Acceptance**: All tasks closed, tests pass, 100% coverage maintained" --json
# Store returned ID as IMPLEMENT_ID

br create "[sp:08-harden] Iterative review + remediation for $FEATURE_NAME" -p 2 --parent <epic-id> \
  --description "**Spec**: specs/$BRANCH/spec.md, plan.md
**Skills**: /security-audit, /clean-architecture-validator, /quality-review, /glossary
**Context**: Loop through security → architecture → code quality reviews, running ralph between each step to fix p1/p2 (CRITICAL/MAJOR) findings. Restart-on-fix policy: any fix re-runs the cycle from security. Exits when three reviews in a row produce zero p1/p2, or after a 5-cycle safety cap.
**Acceptance**: No remaining p1/p2 findings across all three reviews; remediation tasks closed; harden state file deleted." --json
# Store returned ID as HARDEN_ID
```

b. Create the dependency chain (each phase depends on the previous):

```bash
br dep add <RED_TEAM_ID> <PLAN_ID>
br dep add <TASKS_ID> <RED_TEAM_ID>
br dep add <ANALYZE_ID> <TASKS_ID>
br dep add <IMPLEMENT_ID> <ANALYZE_ID>
br dep add <HARDEN_ID> <IMPLEMENT_ID>
```

c. Store phase task IDs in spec.md front matter for reference:

```markdown
**Beads Phase Tasks**:

- plan: `<PLAN_ID>`
- red-team: `<RED_TEAM_ID>`
- tasks: `<TASKS_ID>`
- analyze: `<ANALYZE_ID>`
- implement: `<IMPLEMENT_ID>`
- harden: `<HARDEN_ID>`
```

d. Verify the dependency chain:

```bash
br dep tree <epic-id> --direction up
```

- Note: `--direction up` shows dependents/children (default `down` shows blockers, which is empty for an epic)

Expected output shows the chain: plan → red-team → tasks → analyze → implement → harden

e. If phase task creation fails, log the error and continue. The workflow can still function with manual skill invocation.

11. **Specification Quality Validation**: After writing the spec, validate it against quality criteria:

a. **Create Spec Quality Checklist**: Generate a checklist file at `FEATURE_DIR/checklists/requirements.md` using the checklist template structure with these validation items:

```markdown
# Specification Quality Checklist: [FEATURE NAME]

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: [DATE]
**Feature**: [Link to spec.md]

## Content Quality

- [ ] No implementation details (languages, frameworks, APIs)
- [ ] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [ ] All mandatory sections completed

## Requirement Completeness

- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Requirements are testable and unambiguous
- [ ] Success criteria are measurable
- [ ] Success criteria are technology-agnostic (no implementation details)
- [ ] All acceptance scenarios are defined
- [ ] Edge cases are identified
- [ ] Scope is clearly bounded
- [ ] Dependencies and assumptions identified

## Feature Readiness

- [ ] All functional requirements have clear acceptance criteria
- [ ] User scenarios cover primary flows
- [ ] Feature meets measurable outcomes defined in Success Criteria
- [ ] No implementation details leak into specification

## Notes

- Items marked incomplete require spec updates before `/sp:03-plan`
```

b. **Run Validation Check**: Review the spec against each checklist item:

- For each item, determine if it passes or fails
- Document specific issues found (quote relevant spec sections)

c. **Handle Validation Results**:

- **If all items pass**: Mark checklist complete and proceed to step 12

- **If items fail (excluding [NEEDS CLARIFICATION])**:
  1.  List the failing items and specific issues
  2.  Update the spec to address each issue
  3.  Re-run validation until all items pass (max 3 iterations)
  4.  If still failing after 3 iterations, document remaining issues in checklist notes and warn user

- **If [NEEDS CLARIFICATION] markers remain**:
  1.  Auto-resolve with reasonable defaults where possible, documenting in the Assumptions section
  2.  For any that cannot be auto-resolved, present them to the user one at a time using the interview format from Step 6
  3.  Update the spec after each resolution

d. **Update Checklist**: After each validation iteration, update the checklist file with current pass/fail status

12. **Update The Pin** (`specs/readme.md`):

Add an entry for this new feature to the specs index file so it's discoverable by future agents.

a. Generate 10-20 keywords covering: - Feature name and common synonyms for what it does - Key technologies, libraries, CLI tools named in the spec - Domain terms from `docs/glossary.md` that appear in the spec - How someone would describe this problem _before_ knowing the spec vocabulary

b. Check if an entry already exists in `specs/readme.md` for this feature: - If yes: update the Keywords line in-place - If no: append a new entry before the "How to Update This File" section

c. Entry format:

```## <Feature Title>

      Keywords: kw1, kw2, kw3, ...
      Spec: specs/<BRANCH_NAME>/spec.md
```

d. If `specs/readme.md` does not exist yet, create it (bootstrap from all existing specs first, then add this entry).

e. This step must not block spec creation — if the pin update fails, log a warning and continue.

13. Report completion with:

- Branch name
- Spec file path
- **Beads epic ID** (if created successfully)
- **Phase tasks created** (list all phase task IDs)
- **Dependency chain visualization** (from `br dep tree`)
- Checklist results
- **Next step**: Run `/sp:next` or `/sp:03-plan` to continue

**NOTE:** The script creates and checks out the new branch and initializes the spec file before writing.

## General Guidelines

## Quick Guidelines

- Focus on **WHAT** users need and **WHY**.
- Avoid HOW to implement (no tech stack, APIs, code structure).
- Written for business stakeholders, not developers.
- DO NOT create any checklists that are embedded in the spec. That will be a separate command.

### Section Requirements

- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation

When creating this spec from a user prompt:

1. **Make informed guesses**: Use context, industry standards, and common patterns to fill gaps
2. **Document assumptions**: Record reasonable defaults in the Assumptions section
3. **Limit clarifications**: Use [NEEDS CLARIFICATION] markers only for critical decisions that:
   - Significantly impact feature scope or user experience
   - Have multiple reasonable interpretations with different implications
   - Lack any reasonable default
4. **Prioritize clarifications**: scope > security/privacy > user experience > technical details
5. **Think like a tester**: Every vague requirement should fail the "testable and unambiguous" checklist item
6. **Common areas needing clarification** (only if no reasonable default exists):
   - Feature scope and boundaries (include/exclude specific use cases)
   - User types and permissions (if multiple conflicting interpretations possible)
   - Security/compliance requirements (when legally/financially significant)

**Examples of reasonable defaults** (don't ask about these):

- Data retention: Industry-standard practices for the domain
- Performance targets: Standard web/mobile app expectations unless specified
- Error handling: User-friendly messages with appropriate fallbacks
- Authentication method: Standard session-based or OAuth2 for web apps
- Integration patterns: RESTful APIs unless specified otherwise

### Success Criteria Guidelines

Success criteria must be:

1. **Measurable**: Include specific metrics (time, percentage, count, rate)
2. **Technology-agnostic**: No mention of frameworks, languages, databases, or tools
3. **User-focused**: Describe outcomes from user/business perspective, not system internals
4. **Verifiable**: Can be tested/validated without knowing implementation details

**Good examples**:

- "Users can complete checkout in under 3 minutes"
- "System supports 10,000 concurrent users"
- "95% of searches return results in under 1 second"
- "Task completion rate improves by 40%"

**Bad examples** (implementation-focused):

- "API response time is under 200ms" (too technical, use "Users see results instantly")
- "Database can handle 1000 TPS" (implementation detail, use user-facing metric)
- "React components render efficiently" (framework-specific)
- "Redis cache hit rate above 80%" (technology-specific)

## Beads Error Handling

If beads commands fail during execution:

1. **br init fails**: Display error, suggest installing br via curl, continue without beads
2. **Epic creation fails**: Log warning, continue with spec creation, note in completion report
3. **Epic lookup fails**: Create new epic (may result in duplicate if lookup was false negative)

The specification workflow should complete even if beads integration encounters errors. Beads is an enhancement for task tracking, not a blocker for spec creation.

## Commit Changes

Run the `/sp-commit` skill to stage and commit all changes made during this phase. Do not push.

---

**Subagent policy:** The interview MUST run in the main context — never delegate user interaction to a subagent. Use Explore subagents for non-interactive codebase research (e.g. scanning existing code, reading specs, checking glossary).
