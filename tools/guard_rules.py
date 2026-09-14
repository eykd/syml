"""Deterministic guard rules for the Claude Code ``PreToolUse`` Bash hook.

Ported from ``.claude/hooks/guard-rules.ts`` in the turtlebased-ts repository.
The pipeline mirrors the TypeScript original exactly:

1. :func:`normalize_command` collapses line continuations and strips command
   wrappers (``sudo``, ``env FOO=bar``, ``nohup``, ...).
2. :data:`PRE_STRIP_RULES` and :data:`PLATFORM_RULES` run against the raw
   (normalized) command, so a hook-bypass flag hidden inside quotes still
   blocks.
3. ``bash -c`` / ``eval`` payloads are unwrapped once and evaluated
   recursively.
4. :func:`strip_quoted_content` removes heredocs and quoted strings, the result
   is split on shell separators, and :data:`POST_STRIP_RULES` runs against each
   sub-command independently.

The Cloudflare/wrangler rules of the original are deliberately dropped: this
repository has no Cloudflare surface.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Verdict:
    """A blocked command: the rule that fired and the message to show the agent."""

    rule_id: str
    message: str


@dataclass(frozen=True)
class GuardRule:
    """A named destructive-command pattern with optional safe-pattern escapes."""

    name: str
    category: str
    pattern: re.Pattern[str]
    message: str
    safe_patterns: tuple[re.Pattern[str], ...] = ()


PRE_STRIP_RULES: tuple[GuardRule, ...] = (
    GuardRule(
        name='hook-bypass',
        category='hook-bypass',
        pattern=re.compile(r'git\s+.*(--no-verify|--no-gpg-sign)'),
        message="""BLOCKED: Hook bypass flags detected.

Prohibited flags: --no-verify, --no-gpg-sign

Instead of bypassing safety checks:
- If pre-commit fails: fix the ruff/mypy/pytest errors it found
- If commit-msg fails: write a proper conventional commit message
- If pre-push fails: fix the issues preventing push

Fix the root problem rather than bypassing the safety mechanism.
Only use these flags when explicitly requested by the user.""",
    ),
    GuardRule(
        name='force-push',
        category='destructive-git',
        pattern=re.compile(r'git\s+push.*(--force([^-]|$)|-f(\s|$)|--force-with-lease)'),
        message="""BLOCKED: Force push detected.

Force pushing rewrites remote history and can destroy teammates' work.

Instead:
- Use normal `git push` to push changes safely
- If rejected, pull and merge first: `git pull --rebase` then `git push`
- Force-pushes are performed by a human directly, never by the agent""",
    ),
)

PLATFORM_RULES: tuple[GuardRule, ...] = (
    GuardRule(
        name='gh-repo-delete',
        category='platform-ops',
        pattern=re.compile(r'gh\s+repo\s+delete'),
        message="""BLOCKED: gh repo delete detected.

This command destroys the entire GitHub repository with no recovery path.

Instead:
- Use the GitHub web UI if you truly need to delete a repository
- Use `gh repo archive` to archive instead of deleting
- Confirm with the user before taking any repository-level destructive action""",
    ),
)

POST_STRIP_RULES: tuple[GuardRule, ...] = (
    GuardRule(
        name='reset-hard',
        category='destructive-git',
        pattern=re.compile(r'git\s+reset\s+--hard'),
        message="""BLOCKED: git reset --hard detected.

This command discards all uncommitted changes with no recovery path.

Instead:
- Use `git stash` to save changes temporarily
- Use `git reset --soft HEAD~1` to undo a commit but keep changes
- Use `git checkout -- <file>` to discard changes in a specific file""",
    ),
    GuardRule(
        name='checkout-dot',
        category='destructive-git',
        pattern=re.compile(r'git\s+checkout\s+(--\s+)?\.(\s|$)'),
        message="""BLOCKED: git checkout . detected (discard all changes).

This command discards all uncommitted changes across every file.

Instead:
- Use `git checkout -- <file>` to discard changes in a specific file
- Use `git stash` to save changes temporarily
- Use `git diff` to review changes before discarding""",
    ),
    GuardRule(
        name='checkout-treeish-dot',
        category='destructive-git',
        pattern=re.compile(r'git\s+checkout\s+.*--\s+\.(\s|$)'),
        message="""BLOCKED: git checkout <tree-ish> -- . detected (overwrite all files).

This command overwrites all working tree files from another commit.

Instead:
- Use `git checkout <tree-ish> -- <file>` to restore a specific file
- Use `git diff <tree-ish>` to review differences first
- Use `git stash` to save current changes before restoring""",
    ),
    GuardRule(
        name='restore-dot',
        category='destructive-git',
        pattern=re.compile(r'git\s+restore\s+\.(\s|$)'),
        safe_patterns=(
            re.compile(r'git\s+restore\s+--staged'),
            re.compile(r'git\s+restore\s+-S'),
        ),
        message="""BLOCKED: git restore . detected (discard all changes).

This command discards all uncommitted changes across every file.

Instead:
- Use `git restore <file>` to discard changes in a specific file
- Use `git restore --staged <file>` to unstage specific files
- Use `git stash` to save changes temporarily""",
    ),
    GuardRule(
        name='clean-force',
        category='destructive-git',
        pattern=re.compile(r'git\s+clean\s+.*-[a-zA-Z]*f'),
        safe_patterns=(
            re.compile(r'git\s+clean\s+.*-[a-zA-Z]*n'),
            re.compile(r'git\s+clean\s+.*--dry-run'),
        ),
        message="""BLOCKED: git clean -f detected (delete untracked files).

This command permanently deletes untracked files with no recovery path.

Instead:
- Use `git clean -n` to preview what would be deleted (dry run)
- Use `git clean --dry-run` for the same preview
- Manually remove specific files you no longer need""",
    ),
    GuardRule(
        name='legacy-bd',
        category='platform-ops',
        pattern=re.compile(r'(?:^|&&|\|\||[;(|])\s*(?:npx\s+)?bd(?:\s|$)', re.MULTILINE),
        message="""BLOCKED: `bd` (legacy beads) is not permitted. Use `br` (beads_rust) instead.

This project uses beads_rust.

Replace:
  npx bd <subcommand>
  bd <subcommand>

With:
  br <subcommand>""",
    ),
    GuardRule(
        name='br-init-force',
        category='platform-ops',
        pattern=re.compile(r'\bbr\s+init\b.*(-f\b|--force\b)'),
        message="""BLOCKED: br init --force is not permitted.

Reinitializing the beads database would destroy all issue history.

Instead:
- Use `br init` without --force to initialize safely
- Use `br status` to check current beads state
- Have the user run this manually if a force-reset is genuinely needed""",
    ),
    GuardRule(
        name='commit-amend',
        category='destructive-git',
        pattern=re.compile(r'git\s+commit\s+.*--amend'),
        message="""BLOCKED: git commit --amend detected (amending commits is prohibited).

Never amend commits - create a new commit instead. Amending after a failed
pre-commit hook can destroy the previous commit's changes.

Instead:
- Always create a new commit for changes
- Use `git reset --soft HEAD~1` to undo a commit without losing changes
- Have the user run interactive rebase manually if reorganizing history is needed""",
    ),
    GuardRule(
        name='merge-squash',
        category='destructive-git',
        pattern=re.compile(r'git\s+merge\s+.*--squash'),
        message="""BLOCKED: git merge --squash detected (squash-merging is prohibited).

Never squash-merge - preserve full commit history. Squash-merging destroys PR
commit history and makes debugging harder.

Instead:
- Use normal `git merge` to preserve commit history
- Use `git merge --no-ff` to ensure a merge commit is created
- Have the user perform interactive rebase manually if needed""",
    ),
    GuardRule(
        name='stash-drop',
        category='destructive-git',
        pattern=re.compile(r'git\s+stash\s+drop(?:\s|$)'),
        message="""BLOCKED: git stash drop detected.

This command permanently deletes a stash entry with no recovery path.

Instead:
- Use `git stash list` to review stashes before dropping
- Use `git stash apply` to apply without removing the stash
- Use `git stash pop` to apply and remove only after confirming the contents""",
    ),
    GuardRule(
        name='stash-clear',
        category='destructive-git',
        pattern=re.compile(r'git\s+stash\s+clear(?:\s|$)'),
        message="""BLOCKED: git stash clear detected.

This command permanently deletes all stash entries with no recovery path.

Instead:
- Use `git stash list` to review stashes before clearing
- Use `git stash drop stash@{N}` to remove specific stashes one at a time
- Use `git stash apply` to recover work from a stash before removing it""",
    ),
    GuardRule(
        name='branch-force-delete',
        category='destructive-git',
        pattern=re.compile(r'git\s+branch\s+-D(?:\s|$)'),
        message="""BLOCKED: git branch -D detected (force-delete unmerged branch).

This command deletes a branch even if it has unmerged changes, losing work.

Instead:
- Use `git branch -d <branch>` to safely delete only fully-merged branches
- Use `git log <branch>` to review commits before deleting
- Use `git merge <branch>` to merge changes before deleting""",
    ),
    GuardRule(
        name='catastrophic-rm',
        category='catastrophic-file-deletion',
        pattern=re.compile(
            r'rm\s+(?:-[a-zA-Z]*(?:rf|fr)[a-zA-Z]*|-[a-zA-Z]*r\s+-[a-zA-Z]*f'
            r'|-[a-zA-Z]*f\s+-[a-zA-Z]*r|--recursive\s+--force|--force\s+--recursive)'
            r'\s+(?:\$\{HOME\}|\$HOME|\.\./|\./|~/|/|~|\.|\*)(?:\s|$)'
        ),
        message="""BLOCKED: Catastrophic rm detected - targets system-critical path.

This command would recursively force-delete a critical path (root, home, the
current directory, or all files) with no recovery.

Instead:
- Use `rm -rf <specific-directory>` to remove a known directory
- Use `ls <path>` to verify what would be affected first
- Never use rm -rf with /, ., ~, ../, *, $HOME, or similar broad targets""",
    ),
)


def normalize_command(command: str) -> str:
    """Collapse line continuations and strip leading command wrappers.

    Wrappers (``sudo``, ``command``, ``nohup``, ``exec``, ``time``, ``nice``
    and ``env FOO=bar``) are stripped iteratively until the string stabilizes,
    so chained or doubled wrappers cannot hide a destructive command.

    :param command: The raw command string.
    :returns: The normalized command.
    """
    result = re.sub(r'\\\n\s*', ' ', command)
    result = re.sub(r'^\\', '', result)
    while True:
        prev = result
        result = re.sub(r'^(sudo|command|nohup|exec|time|nice)\s+', '', result)
        result = re.sub(r'^env\s+(\w+=\S+\s+)*', '', result)
        if result == prev:
            return result


def strip_quoted_content(command: str) -> str:
    """Replace heredocs and quoted strings with empty placeholders.

    :param command: The command string.
    :returns: The command with quoted content removed.
    """
    result = re.sub(r"<<-?'?(\w+)'?\n[\s\S]*?\n\s*\1", '', command)
    result = re.sub(r'"(?:[^"\\]|\\.)*"', '""', result)
    return re.sub(r"'[^']*'", "''", result)


def split_commands(command: str) -> list[str]:
    """Split a quote-stripped command on shell separators.

    Each sub-command is evaluated independently so a safe pattern in one
    sub-command cannot whitelist a destructive pattern in another.

    :param command: The quote-stripped command string.
    :returns: The non-empty sub-command strings.
    """
    return [part for part in re.split(r'\s*(?:&&|\|\||[;|])\s*', command) if part]


_SHELL_WRAPPER_RE = re.compile(r'^(?:bash|sh|zsh|dash)\s+-c\s+')
_EVAL_WRAPPER_RE = re.compile(r'^eval\s+')
_MAX_SHELL_DEPTH = 1


def _extract_shell_payload(command: str, prefix: re.Pattern[str]) -> str | None:
    """Strip a shell-wrapper prefix and unquote the remaining payload.

    :param command: The normalized command starting with the wrapper prefix.
    :param prefix: The wrapper prefix pattern that matched.
    :returns: The payload string, or ``None`` when there is nothing after the prefix.
    """
    stripped = prefix.sub('', command, count=1)
    if not stripped:
        return None
    first = stripped[0]
    if first == '"':
        i = 1
        while i < len(stripped):
            if stripped[i] == '\\' and i + 1 < len(stripped):
                i += 2
                continue
            if stripped[i] == '"':
                return stripped[1:i].replace('\\"', '"')
            i += 1
        return stripped[1:]
    if first == "'":
        end = stripped.find("'", 1)
        if end > 0:
            return stripped[1:end]
        return stripped[1:]
    return stripped


def _first_block(rules: tuple[GuardRule, ...], text: str) -> Verdict | None:
    """Return the first rule that blocks ``text``, honouring safe patterns.

    :param rules: The rule table to check, in order.
    :param text: The command text to match against.
    :returns: A :class:`Verdict`, or ``None`` when nothing blocks.
    """
    for rule in rules:
        if any(safe.search(text) for safe in rule.safe_patterns):
            continue
        if rule.pattern.search(text):
            return Verdict(rule_id=rule.name, message=rule.message)
    return None


def _check_shell_wrapper(normalized: str, depth: int) -> Verdict | None:
    """Evaluate the payload of a ``bash -c`` / ``eval`` wrapper, if present.

    :param normalized: The normalized command.
    :param depth: Remaining recursion depth; negative disables unwrapping.
    :returns: A :class:`Verdict` from the payload, or ``None``.
    """
    if depth < 0:
        return None
    payload: str | None = None
    if _SHELL_WRAPPER_RE.search(normalized):
        payload = _extract_shell_payload(normalized, _SHELL_WRAPPER_RE)
    elif _EVAL_WRAPPER_RE.search(normalized):
        payload = _extract_shell_payload(normalized, _EVAL_WRAPPER_RE)
    if payload is None:
        return None
    return _evaluate_inner(payload, depth - 1)


def _evaluate_inner(command: str, depth: int) -> Verdict | None:
    """Run the full guard pipeline against one command string.

    :param command: The command string.
    :param depth: Remaining shell-wrapper recursion depth.
    :returns: A :class:`Verdict` when blocked, else ``None``.
    """
    normalized = normalize_command(command)
    if not normalized.strip():
        return None

    verdict = _first_block(PRE_STRIP_RULES, normalized)
    if verdict is not None:
        return verdict

    verdict = _first_block(PLATFORM_RULES, normalized)
    if verdict is not None:
        return verdict

    verdict = _check_shell_wrapper(normalized, depth)
    if verdict is not None:
        return verdict

    for sub in split_commands(strip_quoted_content(normalized)):
        verdict = _first_block(POST_STRIP_RULES, sub)
        if verdict is not None:
            return verdict
    return None


def evaluate_command(command: str) -> Verdict | None:
    """Evaluate a command against every guard rule.

    :param command: The raw command string from ``tool_input.command``.
    :returns: A :class:`Verdict` when the command must be blocked, else ``None``.
    """
    return _evaluate_inner(command, _MAX_SHELL_DEPTH)
