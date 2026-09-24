# syml Constitution

<!--
Sync Impact Report:
- Version: 1.0.0 → 2.0.0 (MAJOR - principle IV redefined)
- Modified principles:
  - III (Coverage and Lint Gates): dropped the stale nodes.py/parsers.py
    pragma example.
  - IV (Spec vs Implementation Discipline): dropped the claim that the spec
    is aspirational and doesn't describe current behavior; dropped the
    todo.txt-as-ledger framing (todo.txt is being retired, US9 of
    syml-1.0-conformance); citations now point at SYML-SPEC-REVIEW.md's
    D1-D17 decisions, B-/M-numbered findings, and FR-NNN requirements; an
    open spec question may now be settled by a spec edit landing in the same
    commit as the behavior change that exposed it.
- Added sections: None
- Removed sections: None
- Templates requiring updates: .specify/templates/plan-template.md (✅ no
  principle-IV or todo.txt wording present), .specify/templates/
  spec-template.md (✅ no changes needed), .specify/templates/
  checklist-template.md (✅ no changes needed)
- Follow-up TODOs: None
-->

## Preamble

This constitution governs development of `syml`, a small Python parser
library published on PyPI. It exists to keep a line-oriented, context-free
grammar and a 100%-branch-covered implementation from drifting into
undisciplined complexity as the spec (`SYML-SPECIFICATION.md`) and the
implementation converge.

---

## Core Principles

### I. Test-Driven Development (NON-NEGOTIABLE)

All implementation code MUST be preceded by a failing test. The cycle is
Red-Green-Refactor, entered via a Test List:

0. **Test List**: enumerate behavioral variants first (in beads, as leaf task
   titles — a planning artifact, **not** pre-written tests).
1. **Red**: write a failing test first, then commit it via
   `.venv/bin/python -m tools.commit_red` before writing implementation code.
2. **Green**: write the minimal code to pass.
3. **Refactor**: improve the code while keeping tests green.

**Rationale**: A committed RED test is proof the test could fail before the
code existed, which is the only way to trust that a later green run means the
implementation — not the test — is correct.

### II. Type Safety

mypy runs in strict mode over `src/`, `tests/`, and `tools/`. No untyped
function defs; every test function needs a `-> None` return annotation and
every fixture needs a return annotation. `disallow_any_generics` is on, so
generic containers must be parameterized.

**Rationale**: A small parser library lives or dies by precise types on its
public surface (`Source`, `Pos`, the `SymlNode` tree); strict mypy catches
misuse of that surface before it reaches a caller.

### III. Coverage and Lint Gates

100% branch coverage is enforced at commit time and in CI
(`--cov-fail-under=100`), covering `src/` and `tools/`. ruff runs in preview
mode with pydocstyle (`D`) rules enabled. `# pragma: nocover` /
`# pragma: nobranch` are permitted only for provably unreachable branches,
never as a shortcut past an untested path.

**Rationale**: A grammar-driven parser has many structurally-required branches
that ordinary test-writing skips; the 100% gate forces every one of them to be
either exercised or explicitly justified as unreachable.

### IV. Spec vs Implementation Discipline

Any behavior change — in either direction — MUST cite a design decision
(D1–D17) or a B-/M-numbered finding from `SYML-SPEC-REVIEW.md`, or an FR-NNN
requirement from the current feature's plan. An open spec question MUST be
settled (recorded as a decision) before implementing against it, except that
a specification edit MAY land in the same commit as the behavior change that
exposed the question.

**Rationale**: Without this discipline, "fixing" a mismatch between spec and
parser is a coin flip about which one was actually wrong; citing a numbered
decision or requirement makes every behavior change traceable to a considered
choice.

### V. Simplicity / YAGNI

Every leaf value is a plain `str` — this is the library's entire reason to
exist, and no change may introduce a second leaf type. The grammar stays
line-oriented and context-free at the lexing level. No new runtime dependency
may be added without a plan-level justification in the Complexity Tracking
section of that feature's plan.

**Rationale**: syml's value proposition is that it is smaller and stricter
than YAML; every added type, dependency, or context-sensitivity claws that
back.

### VI. Public API Stability

`syml.loads` / `syml.load` signatures, and the semantics of `Source` and
`Pos`, are semver-guarded. A breaking change to either MUST bump the major
version and MUST be listed explicitly in the plan's Constitution Check
section, with the alternative (non-breaking) approach it rejected.

**Rationale**: This is a published library with external consumers; silent
signature or semantics drift breaks callers who pinned a minor version in
good faith.

---

## Governance

### Amendment Procedure

1. Propose the amendment with clear rationale.
2. Identify affected templates (`.specify/templates/*`) and code.
3. Create a migration plan for existing code if the amendment changes
   established behavior.
4. Update this constitution with a version bump.
5. Propagate changes to all dependent templates.
6. Update `CLAUDE.md` if runtime guidance to Claude Code is affected.
7. Commit with message: `docs: amend constitution to vX.Y.Z (summary)`.

### Versioning Policy

This constitution follows semantic versioning:

- **MAJOR**: Backward-incompatible principle removals or redefinitions.
- **MINOR**: A new principle or section added, or materially expanded
  guidance.
- **PATCH**: Clarifications, wording, typo fixes, non-semantic refinements.

### Compliance Review

- This constitution supersedes all other practices and documentation.
- Every plan MUST pass the Constitution Check gate before Phase 0 research,
  re-checked after Phase 1 design.
- Any complexity introduced MUST be justified in Complexity Tracking.
- Violations require either a fix or a constitutional amendment — never a
  silent exception.
- Use `CLAUDE.md` for day-to-day runtime guidance to Claude Code.

**Version**: 2.0.0 | **Ratified**: 2026-09-13 | **Last Amended**: 2026-09-23
