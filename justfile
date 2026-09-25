# syml task runner. `just --list` shows every recipe.
# Wraps the uv toolchain so the spec-kit workflow (.claude/commands/sp/) can
# call stable recipe names. runtests.sh / watchtests.sh remain the fast loop.

# List all available commands
default:
    @just --list

# Install runtime + dev + test groups
install:
    uv sync --all-groups

# Run the unit suite (pyproject addopts add coverage, random order, and skip acceptance)
test:
    uv run pytest

# Run the unit suite and enforce the 100% coverage gate (what pre-commit and CI run)
test-coverage:
    uv run pytest --cov-fail-under=100

# Lint with ruff (preview mode, pydocstyle D rules)
lint:
    uv run ruff check

# Lint with auto-fix
lint-fix:
    uv run ruff check --fix

# Format with ruff
format:
    uv run ruff format

# Fix all auto-fixable issues (ralph's prep.sh calls this before each task)
fix: format lint-fix
    @echo "✅ Auto-fixes applied!"

# Type-check with mypy (file set is configured in pyproject)
type-check:
    uv run mypy

# Run all quality checks (pre-commit suite minus the coverage gate)
check: lint type-check test
    @echo "✅ All checks passed!"

# ============================================================================
# Acceptance Test Pipeline (pytest-bdd)
# ============================================================================

# Gherkin features live in specs/acceptance-specs/US<NN>-<slug>.feature and are
# bound by tests/acceptance/test_us<nn>_<slug>.py. The unit run ignores that
# directory entirely (see pyproject addopts), so acceptance only ever runs here.
# `-o addopts=""` drops the unit run's `-m "not acceptance"` and `--ignore`.

# Run the acceptance suite. Unbound scenarios fail with StepDefinitionNotFoundError (the RED marker).
# Excludes @release scenarios (US13 scenario 7): they only pass after the 1.0.0
# tag is pushed, so they must never gate a CI push (plan.md § Acceptance Test
# Strategy, red team outer iteration 10).
acceptance:
    uv run pytest tests/acceptance -m "acceptance and not release" --no-cov -o addopts="" -p no:random_order

# Run only the @release-tagged scenarios. Run by hand in the release leaf, after `git push origin 1.0.0`.
release-check:
    uv run pytest tests/acceptance -m release --no-cov -o addopts="" -p no:random_order

# List every step that has no binding yet, as ready-to-paste stubs. pytest-bdd exits 100 when steps are missing, hence `|| true`.
acceptance-missing:
    uv run pytest tests/acceptance -m acceptance --no-cov -o addopts="" -p no:random_order --generate-missing --feature specs/acceptance-specs || true

# Run both unit tests and acceptance tests
test-all: test acceptance

# Run the round-trip property suite at high volume (thousands of examples per
# property, non-deterministic). Hand-run only; the commit gate runs the
# `gate` profile (a few hundred, derandomized) as part of `just test`.
fuzz:
    HYPOTHESIS_PROFILE=fuzz uv run pytest tests/test_roundtrip_property.py --no-cov --hypothesis-show-statistics

# Build the sdist and wheel into dist/ (what the release workflow uploads to PyPI)
build:
    uv build

# ============================================================================
# Beads Task Tracker
# ============================================================================

# Pinned beads_rust (br) release. Minimum safe is 0.5.5: every earlier build
# has a cross-process WAL checkpoint race (beads_rust#457) that silently drops
# issues and dependency edges under concurrent use. Keep in sync with
# .claude/skills/install-br/SKILL.md.
br_version := "0.5.7"

# Initialize beads database from tracked JSONL (run after fresh clone)
beads-init:
    #!/usr/bin/env bash
    set -euo pipefail
    # Ensure br (beads_rust) is installed at the pinned release
    if ! command -v br &>/dev/null || [ "$(br --version | awk '{print $2}')" != "{{br_version}}" ]; then
        echo "Installing beads_rust {{br_version}}..."
        case "$(uname -s)-$(uname -m)" in
            Darwin-arm64)  asset="br-{{br_version}}-darwin_arm64.tar.gz" ;;
            Darwin-x86_64) asset="br-{{br_version}}-darwin_amd64.tar.gz" ;;
            Linux-aarch64) asset="br-{{br_version}}-linux_arm64.tar.gz" ;;
            Linux-x86_64)  asset="br-{{br_version}}-linux_amd64.tar.gz" ;;
            *) echo "unsupported platform: $(uname -s)-$(uname -m)"; exit 1 ;;
        esac
        if command -v gh &>/dev/null; then
            tmp=$(mktemp -d)
            gh release download "v{{br_version}}" -R Dicklesworthstone/beads_rust \
                -p "$asset" -p "$asset.sha256" -D "$tmp"
            (cd "$tmp" && shasum -a 256 -c "$asset.sha256")
            tar xzf "$tmp/$asset" -C "$tmp"
            mkdir -p ~/.local/bin && install -m 755 "$tmp/br" ~/.local/bin/br
            rm -rf "$tmp"
        else
            # No gh: upstream installer, pinned via --version (no checksum step).
            curl -fsSL "https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/install.sh?$(date +%s)" \
                | bash -s -- --version "v{{br_version}}"
        fi
        export PATH="$HOME/.local/bin:$PATH"
    fi
    # Rebuild the local DB from the committed JSONL. A beads.db written by
    # br < 0.5.x (schema 5) is refused by 0.5.x (schema 17) and is very likely
    # already malformed, so never migrate it — delete and rebuild. Flush first
    # so a healthy DB with un-exported writes is not silently discarded
    # (--rebuild treats JSONL as authoritative); on a refused DB the flush
    # simply errors and is ignored. `--db` is explicit so a stale ~/.beads
    # higher up the tree is never auto-discovered instead of this repo's.
    br --db .beads/beads.db sync --flush-only >/dev/null 2>&1 || true
    rm -f .beads/beads.db .beads/beads.db-wal .beads/beads.db-shm .beads/.local_version
    br --db .beads/beads.db sync --import-only --rebuild
    rm -rf .beads/.br_recovery
    # `br doctor` exits 1 on any WARN (even benign ones); report, don't fail.
    br doctor || echo "⚠️  br doctor reported findings above — review before running a drain"
    echo "✅ Beads initialized (br $(br --version | awk '{print $2}'))"
