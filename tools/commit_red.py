"""``commit-red`` - guarded self-commit for a RED TDD task.

Ported from ``.claude/skills/ralph/commit-red.ts`` in the turtlebased-ts
repository, retargeted at this repo's uv/pytest/pre-commit toolchain.

Commits a *known-failing* test for a RED beads task locally, skipping ONLY the
``pytest-check`` pre-commit hook (ruff, mypy and uv-lock still run). It does not
push: the following Green task's push carries this commit as a non-tip
ancestor, so CI never sees a red branch tip.

This is a pure decision procedure - its outcome is a deterministic function of
the beads record (``br show``), the git index, and the staged tests' result. All
``br``/``git``/``pytest`` calls live behind the :class:`Io` seam, so the
decision core is unit-testable without a live repo.

It is NOT a ``--no-verify`` bypass: it refuses loudly unless the task really is
a RED task and the staged tests really fail.

Invoked as ``.venv/bin/python -m tools.commit_red <task-id>``.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import PurePosixPath
from typing import Protocol

#: Environment variable pre-commit reads to skip named hooks.
SKIP_ENV = 'SKIP'

#: The single hook a RED commit is allowed to skip. Everything else still runs.
SKIP_HOOKS = 'pytest-check'

#: Maximum conventional-commit header length.
HEADER_MAX_LENGTH = 100

_RED_TITLE_RE = re.compile(r'^\s*red:', re.IGNORECASE)
_RED_MARKER_RE = re.compile(r'\*\*Type\*\*:\s*RED', re.IGNORECASE)
_RED_PREFIX_RE = re.compile(r'^\s*red:\s*', re.IGNORECASE)


class Io(Protocol):
    """The injected IO boundary: everything :func:`run` needs from the outside world."""

    def br_show(self, task_id: str) -> dict[str, object] | None:
        """Fetch a beads task record, or ``None`` when it cannot be read."""
        ...

    def staged_files(self) -> list[str]:
        """Return the staged file paths."""
        ...

    def tests_fail(self, files: list[str]) -> bool:
        """Run pytest on the given files; ``True`` when they FAIL."""
        ...

    def git_commit(self, message: str) -> int:
        """Commit locally with the pytest hook skipped; return git's exit code."""
        ...

    def out(self, message: str) -> None:
        """Emit an informational line on stdout."""
        ...

    def err(self, message: str) -> None:
        """Emit a refusal or diagnostic line on stderr."""
        ...


def _field(task: dict[str, object], name: str) -> str:
    """Read a string field from a beads record, defaulting to the empty string.

    :param task: The beads task record.
    :param name: The field name.
    :returns: The field value when it is a string, else ``''``.
    """
    value = task.get(name)
    return value if isinstance(value, str) else ''


def is_red_task(task_json: dict[str, object]) -> bool:
    """True when the task is a RED TDD task.

    A task is RED when its title starts with ``Red:`` (case-insensitive) or its
    description carries the ``**Type**: RED`` marker.

    :param task_json: The beads task record.
    :returns: Whether the task is a RED task.
    """
    if _RED_TITLE_RE.search(_field(task_json, 'title')):
        return True
    return bool(_RED_MARKER_RE.search(_field(task_json, 'description')))


def is_test_file(path: str) -> bool:
    """True when a path names a pytest test module.

    Matches this repo's collection convention: a ``.py`` file whose basename
    starts with ``test_`` or ends with ``_test.py``.

    :param path: A repository-relative file path.
    :returns: Whether the path names a test file.
    """
    name = PurePosixPath(path).name
    if not name.endswith('.py'):
        return False
    return name.startswith('test_') or name.endswith('_test.py')


def staged_test_files(paths: list[str]) -> list[str]:
    """The test files among the given staged paths, in order.

    :param paths: All staged file paths.
    :returns: Only the test files.
    """
    return [path for path in paths if is_test_file(path)]


def build_subject(task: dict[str, object]) -> str:
    """Build the conventional-commit header mechanically from the task title.

    The ``Red:`` prefix is stripped and a ``[skip ci]`` marker appended. The
    task id is deliberately absent so the header stays within
    :data:`HEADER_MAX_LENGTH`; it lives in the ``Refs:`` footer instead.

    :param task: The beads task record.
    :returns: A header of the form ``test: red — <behavior> [skip ci]``.
    """
    stripped = _RED_PREFIX_RE.sub('', _field(task, 'title')).strip()
    behavior = stripped or 'write failing test'
    return f'test: red — {behavior} [skip ci]'


def build_commit_message(task: dict[str, object], task_id: str) -> str:
    """Build the full commit message: subject plus a ``Refs:`` footer.

    :param task: The beads task record.
    :param task_id: The beads task ID.
    :returns: The commit message.
    """
    return f'{build_subject(task)}\n\nRefs: {task_id}'


def run(argv: list[str], io: Io) -> int:
    """The guarded decision procedure.

    Each gate refuses loudly before any commit happens. Returns 0 only after a
    failing staged test has been committed locally.

    :param argv: Positional arguments; the task ID is expected at index 0.
    :param io: The injected IO boundary.
    :returns: A process exit code (0 = committed, non-zero = refused/failed).
    """
    if not argv or not argv[0].strip():
        io.err('commit-red: missing required task ID.\n' 'Usage: .venv/bin/python -m tools.commit_red <task-id>')
        return 1
    task_id = argv[0].strip()

    task = io.br_show(task_id)
    if task is None:
        io.err(f'commit-red: task {task_id} not found (br show failed).')
        return 1
    if not is_red_task(task):
        io.err(
            f'commit-red commits a known-failing test for a RED TDD task ONLY. '
            f'Task {task_id} is not a RED task. '
            f'This is NOT a way to bypass failing tests - fix your test.'
        )
        return 1

    subject = build_subject(task)
    if len(subject) > HEADER_MAX_LENGTH:
        io.err(
            f'commit-red: the RED task title is too long for a {HEADER_MAX_LENGTH}-char '
            f'commit header (subject is {len(subject)} chars). '
            f'This is NOT a test/lint failure.\n'
            f'Shorten the beads task title and retry, e.g.:\n'
            f'  br update {task_id} --title "Red: <shorter behavior>"\n'
            f'  .venv/bin/python -m tools.commit_red {task_id}'
        )
        return 1

    files = staged_test_files(io.staged_files())
    if not files:
        io.err(
            'commit-red: no staged test file (tests/**/test_*.py or *_test.py). '
            'Stage the failing test (git add) before committing a RED task.'
        )
        return 1

    if not io.tests_fail(files):
        io.err('commit-red: a RED commit must contain a failing test; these pass - ' 'did you mean a GREEN task?')
        return 1

    message = build_commit_message(task, task_id)
    code = io.git_commit(message)
    if code != 0:
        io.err(
            f'commit-red: commit failed (git exited {code}). ruff/mypy still run on a '
            f'RED commit - this is NOT a bypass, fix the reported errors.'
        )
        return code
    io.out(f'commit-red: committed failing test locally - "{message}". Not pushed.')
    return 0


class RealIo:
    """The production IO boundary: shells out to ``br``, ``git`` and ``pytest``."""

    def br_show(self, task_id: str) -> dict[str, object] | None:
        """Fetch a beads task record via ``br show <id> --json``.

        :param task_id: The beads task ID.
        :returns: The record, or ``None`` when it cannot be read or parsed.
        """
        try:
            result = subprocess.run(
                ['br', 'show', task_id, '--json'],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return None
        if result.returncode != 0:
            return None
        try:
            parsed = json.loads(result.stdout)
        except ValueError:
            return None
        record = parsed[0] if isinstance(parsed, list) and parsed else parsed
        if not isinstance(record, dict):
            return None
        return record

    def staged_files(self) -> list[str]:
        """Return the staged file paths via ``git diff --cached --name-only``.

        :returns: The staged paths, blank lines dropped.
        """
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only'],
            capture_output=True,
            text=True,
            check=False,
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def tests_fail(self, files: list[str]) -> bool:
        """Run pytest on the given files, bypassing the project's default addopts.

        :param files: The staged test files.
        :returns: ``True`` when pytest exits non-zero.
        """
        result = subprocess.run(
            ['uv', 'run', 'pytest', *files, '--no-cov', '-o', 'addopts=', '-q'],
            check=False,
        )
        return result.returncode != 0

    def git_commit(self, message: str) -> int:
        """Commit locally with only the pytest pre-commit hook skipped.

        No ``--no-verify``: the full hook suite runs, minus ``pytest-check``.

        :param message: The commit message.
        :returns: git's exit code.
        """
        env = {**os.environ, SKIP_ENV: SKIP_HOOKS}
        result = subprocess.run(['git', 'commit', '-m', message], env=env, check=False)
        return result.returncode

    def out(self, message: str) -> None:
        """Write an informational line to stdout.

        :param message: The line to write.
        """
        print(message)

    def err(self, message: str) -> None:
        """Write a refusal or diagnostic line to stderr.

        :param message: The line to write.
        """
        print(message, file=sys.stderr)


def main() -> int:
    """Wire the real IO boundary to :func:`run`.

    :returns: The process exit code.
    """
    return run(sys.argv[1:], RealIo())


if __name__ == '__main__':  # pragma: nocover
    raise SystemExit(main())
