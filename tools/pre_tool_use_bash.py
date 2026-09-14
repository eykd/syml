"""Claude Code ``PreToolUse`` hook for the Bash tool.

Reads the hook payload from stdin, extracts ``tool_input.command``, and runs it
through :mod:`tools.guard_rules`. Exit 2 blocks the command and shows the rule
message to the agent; exit 0 allows it.

The hook fails OPEN: a payload that is not JSON, not an object, or carries no
string command is allowed through with a one-line note on stderr. A guard hook
that crashes must never wedge the session.

Invoked as ``.venv/bin/python -m tools.pre_tool_use_bash``.
"""

import json
import sys

from tools.guard_rules import evaluate_command

ALLOW = 0
BLOCK = 2


def extract_command(raw: str) -> str | None:
    """Pull ``tool_input.command`` out of a raw hook payload.

    :param raw: The raw stdin text.
    :returns: The command string, or ``None`` when the payload has no usable one.
    """
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    tool_input = data.get('tool_input')
    if not isinstance(tool_input, dict):
        return None
    command = tool_input.get('command')
    if not isinstance(command, str):
        return None
    return command


def main() -> int:
    """Read the hook payload from stdin and return the hook exit code.

    :returns: ``0`` to allow the command, ``2`` to block it.
    """
    command = extract_command(sys.stdin.read())
    if command is None:
        print('guard-hook: no parseable tool_input.command, allowing', file=sys.stderr)
        return ALLOW
    verdict = evaluate_command(command)
    if verdict is None:
        return ALLOW
    print(verdict.message, file=sys.stderr)
    return BLOCK


if __name__ == '__main__':  # pragma: nocover
    raise SystemExit(main())
