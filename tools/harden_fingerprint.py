"""Write ``.sp-harden-findings.json`` for the ``/sp:08-harden`` orchestrator.

Ported from the ``node -e`` fingerprint block in the turtlebased-ts
``sp-*-review`` agents, so every review phase produces fingerprints an
orchestrator can compare across cycles instead of hashing by hand.

Reads a JSON array of findings on stdin:

.. code-block:: json


    [{"category": "...", "file": "...", "title": "...",
      "severity": "CRITICAL|MAJOR|MINOR", "line": 12, "task_id": "syml-42"}]

and writes the shape the orchestrator reads:

.. code-block:: json


    {"phase": "security-review",
     "criticalCount": 1, "highCount": 0, "mediumCount": 2,
     "taskIds": ["syml-42"],
     "fingerprints": ["<sha1 hex>"],
     "priorities": [1, 2, 3],
     "timestamp": "2026-09-13T12:00:00+00:00"}

``criticalCount``/``highCount``/``mediumCount`` and ``priorities`` (1/2/3) are
both derived from each finding's ``severity``. ``fingerprints`` and
``priorities`` are parallel to the input array's order.

Invoked as
``.venv/bin/python -m tools.harden_fingerprint --phase <phase> < findings.json``.
"""

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

DEFAULT_OUT = '.sp-harden-findings.json'

#: Severity -> count bucket and remediation-task priority. Any other
#: severity is rejected (exit 1); the agents only ever emit these three.
PRIORITY_BY_SEVERITY = {'CRITICAL': 1, 'MAJOR': 2, 'MINOR': 3}

_UNWANTED_RE = re.compile(r'[^a-z0-9\s]')
_WHITESPACE_RE = re.compile(r'\s+')


def normalize_title(title: str) -> str:
    r"""Normalize a finding title for fingerprinting.

    Lowercases, strips every character outside ``[a-z0-9\s]``, collapses runs
    of whitespace to a single space, and trims the ends.

    :param title: The raw finding title.
    :returns: The normalized title.
    """
    lowered = _UNWANTED_RE.sub('', title.lower())
    return _WHITESPACE_RE.sub(' ', lowered).strip()


def fingerprint(finding: dict[str, object]) -> str:
    """Compute a finding's stable identity hash.

    ``sha1("|".join([category, file, normalize_title(title)]))``.

    :param finding: One finding record.
    :returns: The 40-character hex digest.
    """
    parts = [
        str(finding.get('category', '')),
        str(finding.get('file', '')),
        normalize_title(str(finding.get('title', ''))),
    ]
    return hashlib.sha1('|'.join(parts).encode(), usedforsecurity=False).hexdigest()


def _severity(finding: dict[str, object]) -> str:
    """Read a finding's severity, upper-cased.

    :param finding: One finding record.
    :returns: The severity string.
    """
    return str(finding.get('severity', '')).upper()


def build_output(
    phase: str,
    findings: Sequence[dict[str, object]],
    timestamp: datetime,
) -> dict[str, object]:
    """Build the orchestrator-facing findings summary.

    Every finding's ``severity`` must already be one of
    :data:`PRIORITY_BY_SEVERITY` - validate with :func:`_parse_findings` first.

    :param phase: The review phase name.
    :param findings: The findings, in the order their tasks were filed.
    :param timestamp: The generation time (injected so tests stay deterministic).
    :returns: The summary object written to the output file.
    """
    severities = [_severity(finding) for finding in findings]
    return {
        'phase': phase,
        'criticalCount': severities.count('CRITICAL'),
        'highCount': severities.count('MAJOR'),
        'mediumCount': severities.count('MINOR'),
        'taskIds': [str(finding['task_id']) for finding in findings if finding.get('task_id') is not None],
        'fingerprints': [fingerprint(finding) for finding in findings],
        'priorities': [PRIORITY_BY_SEVERITY[severity] for severity in severities],
        'timestamp': timestamp.isoformat(),
    }


def _parse_findings(raw: str) -> list[dict[str, object]]:
    """Parse the stdin payload into a list of finding records.

    :param raw: The raw stdin text.
    :returns: The findings.
    :raises ValueError: When the payload is not valid JSON, or a finding carries
        a severity outside ``CRITICAL``/``MAJOR``/``MINOR``.
    :raises TypeError: When the payload is not an array of objects.
    """
    data = json.loads(raw)
    if not isinstance(data, list):
        raise TypeError('expected a JSON array of findings')
    if not all(isinstance(item, dict) for item in data):
        raise TypeError('every finding must be a JSON object')
    for finding in data:
        severity = _severity(finding)
        if severity not in PRIORITY_BY_SEVERITY:
            known = '/'.join(PRIORITY_BY_SEVERITY)
            message = f'unknown severity {severity!r} (expected one of {known})'
            raise ValueError(message)
    return data


def main(
    argv: list[str] | None = None,
    stdin: TextIO | None = None,
    now: datetime | None = None,
) -> int:
    """Read findings from stdin and write the summary file.

    :param argv: Command-line arguments (defaults to ``sys.argv[1:]``).
    :param stdin: The input stream (defaults to ``sys.stdin``).
    :param now: The generation time (defaults to the current UTC time).
    :returns: ``0`` on success, ``1`` on malformed input.
    """
    parser = argparse.ArgumentParser(prog='harden_fingerprint', description=__doc__)
    parser.add_argument('--phase', required=True, help='the review phase name')
    parser.add_argument('--out', default=DEFAULT_OUT, help='output path')
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    try:
        findings = _parse_findings((sys.stdin if stdin is None else stdin).read())
    except (ValueError, TypeError) as exc:
        print(f'harden_fingerprint: malformed findings input: {exc}', file=sys.stderr)
        return 1

    output = build_output(args.phase, findings, now if now is not None else datetime.now(UTC))
    Path(args.out).write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':  # pragma: nocover
    raise SystemExit(main())
