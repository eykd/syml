---
name: install-br
description: Install or update the beads_rust (`br`) CLI to the pinned release. Use when `br` is not found, is older than the minimum safe version (0.5.5), or `br doctor` reports SCHEMA_MISMATCH / integrity_check after an upgrade.
user_invocable: true
---

# Install beads_rust (`br`) CLI

## Version policy

| Setting        | Value                                                    |
| -------------- | -------------------------------------------------------- |
| Pinned release | `0.5.7` (`BR_VERSION` below)                             |
| Minimum safe   | `0.5.5`                                                  |
| Release page   | https://github.com/Dicklesworthstone/beads_rust/releases |

**Why the floor is 0.5.5.** Every `br` build before 0.5.5 has a cross-process
WAL checkpoint race in its embedded FrankenSQLite engine (beads_rust#457,
frankensqlite#385/#399). Under concurrent use — a ralph or ben drain, several
agents touching `.beads/` at once — it silently dropped issues and dependency
edges, and left the database reporting `integrity_check: page N is never
used`. 0.5.5 fixed the engine; 0.5.6 and 0.5.7 fixed further silent-loss bugs
in export and rebuild. Blind `br doctor --repair` retries do not fix any of
this and were removed from the orchestration scripts. Do not run a drain on an
older build.

## Steps

1. Check the current state:

   ```bash
   command -v br && br --version
   ```

   If the printed version is `>= 0.5.5`, stop — nothing to do (unless the user
   asked to move to the pinned release).

2. Install the pinned release binary from the GitHub release tarball, verifying
   the published SHA-256. This needs network access (run outside the sandbox)
   and `gh` authenticated to GitHub:

   ```bash
   BR_VERSION=0.5.7
   case "$(uname -s)-$(uname -m)" in
     Darwin-arm64)  ASSET="br-${BR_VERSION}-darwin_arm64.tar.gz" ;;
     Darwin-x86_64) ASSET="br-${BR_VERSION}-darwin_amd64.tar.gz" ;;
     Linux-aarch64) ASSET="br-${BR_VERSION}-linux_arm64.tar.gz" ;;
     Linux-x86_64)  ASSET="br-${BR_VERSION}-linux_amd64.tar.gz" ;;
     *) echo "unsupported platform"; exit 1 ;;
   esac
   TMP=$(mktemp -d)
   gh release download "v${BR_VERSION}" -R Dicklesworthstone/beads_rust \
     -p "$ASSET" -p "$ASSET.sha256" -D "$TMP"
   (cd "$TMP" && shasum -a 256 -c "$ASSET.sha256")
   tar xzf "$TMP/$ASSET" -C "$TMP"
   mkdir -p ~/.local/bin && install -m 755 "$TMP/br" ~/.local/bin/br
   rm -rf "$TMP"
   ```

   Fallback without `gh`: the upstream installer, pinned via its `--version`
   flag (it also honours a `VERSION` env var; omit both and it installs
   latest):

   ```bash
   curl -fsSL "https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/install.sh?$(date +%s)" \
     | bash -s -- --version v0.5.7
   ```

3. Verify:

   ```bash
   br --version   # must print the pinned version
   ```

   If `br` is not found, `~/.local/bin` is probably not on PATH:

   ```
   export PATH="$HOME/.local/bin:$PATH"
   ```

4. **Rebuild every local `beads.db` after crossing into 0.5.x.** The 0.5.x
   engine uses schema 17; a 0.1.x database is schema 5 and 0.5.x refuses to
   open it with a `SCHEMA_MISMATCH` error ("ordinary commands never migrate an
   existing tracker database"). Do not migrate it — the old file is very
   likely already malformed. Delete it and rebuild from the committed JSONL,
   which is the source of truth:

   ```bash
   cd <repo>
   br sync --flush-only || true   # export any un-flushed writes first (errors harmlessly on a refused DB)
   rm -f .beads/beads.db .beads/beads.db-wal .beads/beads.db-shm .beads/.local_version
   br sync --import-only --rebuild
   br doctor            # expect HEALTH workspace: healthy, no integrity_check WARN
   br stats             # counts must match what the JSONL held
   rm -rf .beads/.br_recovery   # local vacuum backups written by the rebuild; safe to prune
   ```

   Note `br doctor` exits 1 whenever any WARN is present, benign or not, so
   read the lines rather than the exit code; `br doctor --repair` exits 0 when
   there is nothing to repair. `just beads-init` runs this whole sequence.

   If the rebuild fails on an older store, two known causes, neither is data
   loss:
   - "Import semantic verification failed: issue does not match its
     normalized JSONL payload" — records predate the `source_repo_path`
     field. Run `br sync --migrate-source-repo-path` (prints a plan and a
     SHA), then apply it with the printed SHA:
     `br sync --migrate-source-repo-path --apply --expect-plan-sha256 <sha>`
     and rerun the rebuild.
   - JSON schema errors on `ephemeral`, `crystallizes`, `is_template`,
     `no_history`, or `pinned` — a very old export wrote `0`/`1` instead of
     booleans. Rewrite those five keys to `false`/`true` in `issues.jsonl`
     and rerun the rebuild.

   The binary is global (`~/.local/bin/br`), so this step applies to **every**
   repository on the machine with a `.beads/` directory, on its first touch
   after the upgrade. Find them with:

   ```bash
   find ~/code -maxdepth 4 -type d -name .beads
   ```

5. Refresh `.beads/.gitignore` if `br doctor` warns
   `gitignore.beads_inner_present ... missing expected pattern(s)`: 0.5.x
   writes new sidecars (`*-fsqlite-ns-*`, `*.db-wal-cert*`,
   `*.fsqlite-migration-state`, `.br_recovery/`, `.br-*.lock`). Run
   `br init --prefix x` in a scratch directory and merge its `.beads/.gitignore`
   into the repo's, keeping any repo-specific entries.

6. Report the installed version to the user.

## Bumping the pin

Check `gh release list -R Dicklesworthstone/beads_rust --limit 5`, read the
changelog for the new tag, update `BR_VERSION` here and in `justfile`
(`beads-init`), and rerun step 4 in this repo. Follow-up already known: 0.5.8
(unreleased at time of writing) fixes `doctor --repair` discarding the
`events` / `gate_results` history tables — take it when it ships.
