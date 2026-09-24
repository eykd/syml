import hashlib
import io as io_module
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tools import harden_fingerprint
from tools.harden_fingerprint import build_output, fingerprint, normalize_title

FIXED_NOW = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)

FINDING: dict[str, object] = {
    'category': 'injection',
    'file': 'src/syml/parsers.py',
    'title': 'Unsafe eval() in the Node visitor!',
    'severity': 'CRITICAL',
    'line': 42,
    'task_id': 'syml-42',
}


class TestNormalizeTitle:
    @pytest.mark.parametrize(
        ('raw', 'expected'),
        [
            ('Unsafe eval() in the Node visitor!', 'unsafe eval in the node visitor'),
            ('  Leading   and trailing  ', 'leading and trailing'),
            ('Tabs\tand\nnewlines', 'tabs and newlines'),
            ('MiXeD CaSe 123', 'mixed case 123'),
            ('!!!', ''),
        ],
    )
    def test_it_should_normalize(self, raw: str, expected: str) -> None:
        assert normalize_title(raw) == expected


class TestFingerprint:
    def test_it_should_match_a_sha1_of_the_joined_parts(self) -> None:
        expected = hashlib.sha1(
            b'injection|src/syml/parsers.py|unsafe eval in the node visitor',
            usedforsecurity=False,
        ).hexdigest()
        assert fingerprint(FINDING) == expected

    def test_it_should_produce_a_known_40_hex_digest(self) -> None:
        assert fingerprint(FINDING) == 'f393af27d7b08b178857089542fb7d370f2de7b0'

    def test_it_should_ignore_fields_outside_the_identity_triple(self) -> None:
        other = {**FINDING, 'severity': 'MINOR', 'line': 99, 'task_id': 'syml-99'}
        assert fingerprint(other) == fingerprint(FINDING)

    def test_it_should_tolerate_missing_fields(self) -> None:
        assert len(fingerprint({})) == 40


class TestBuildOutput:
    def test_it_should_count_severities_and_derive_priorities(self) -> None:
        findings: list[dict[str, object]] = [
            {'category': 'a', 'file': 'f', 'title': 'A', 'severity': 'CRITICAL', 'task_id': 't1'},
            {'category': 'b', 'file': 'f', 'title': 'B', 'severity': 'MAJOR'},
            {'category': 'c', 'file': 'f', 'title': 'C', 'severity': 'MINOR', 'task_id': 't3'},
        ]
        output = build_output('security-review', findings, FIXED_NOW)
        assert output['phase'] == 'security-review'
        assert output['criticalCount'] == 1
        assert output['highCount'] == 1
        assert output['mediumCount'] == 1
        assert output['taskIds'] == ['t1', 't3']
        assert output['priorities'] == [1, 2, 3]
        assert output['fingerprints'] == [fingerprint(finding) for finding in findings]
        assert output['timestamp'] == '2026-09-13T12:00:00+00:00'

    def test_it_should_handle_an_empty_findings_array(self) -> None:
        output = build_output('code-quality-review', [], FIXED_NOW)
        assert output['criticalCount'] == 0
        assert output['taskIds'] == []
        assert output['fingerprints'] == []
        assert output['priorities'] == []


class TestMain:
    def test_it_should_write_the_default_file_in_the_cwd(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.chdir(tmp_path)
        stdin = io_module.StringIO(json.dumps([FINDING]))
        assert harden_fingerprint.main(['--phase', 'security-review'], stdin, FIXED_NOW) == 0
        written = json.loads((tmp_path / '.sp-harden-findings.json').read_text())
        assert written['phase'] == 'security-review'
        assert written['fingerprints'] == [fingerprint(FINDING)]

    def test_it_should_honour_an_explicit_out_path(self, tmp_path: Path) -> None:
        out = tmp_path / 'nested' / 'findings.json'
        out.parent.mkdir()
        stdin = io_module.StringIO('[]')
        argv = ['--phase', 'architecture-review', '--out', str(out)]
        assert harden_fingerprint.main(argv, stdin, FIXED_NOW) == 0
        assert json.loads(out.read_text())['phase'] == 'architecture-review'

    def test_it_should_default_the_timestamp_to_now(self, tmp_path: Path) -> None:
        out = tmp_path / 'findings.json'
        argv = ['--phase', 'p', '--out', str(out)]
        assert harden_fingerprint.main(argv, io_module.StringIO('[]')) == 0
        assert json.loads(out.read_text())['timestamp'] != ''

    def test_it_should_read_sys_stdin_by_default(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        out = tmp_path / 'findings.json'
        monkeypatch.setattr('sys.stdin', io_module.StringIO('[]'))
        assert harden_fingerprint.main(['--phase', 'p', '--out', str(out)], None, FIXED_NOW) == 0
        assert out.exists()

    def test_it_should_read_sys_argv_by_default(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        out = tmp_path / 'findings.json'
        monkeypatch.setattr('sys.argv', ['harden_fingerprint', '--phase', 'p', '--out', str(out)])
        assert harden_fingerprint.main(None, io_module.StringIO('[]'), FIXED_NOW) == 0
        assert out.exists()

    @pytest.mark.parametrize('raw', ['not json', '{}', '[1, 2]', '[{"severity": "BLOCKER"}]'])
    def test_it_should_exit_1_on_malformed_input(
        self, raw: str, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        argv = ['--phase', 'p', '--out', str(tmp_path / 'findings.json')]
        assert harden_fingerprint.main(argv, io_module.StringIO(raw), FIXED_NOW) == 1
        assert 'malformed findings input' in capsys.readouterr().err


class TestSeverityMapping:
    @pytest.mark.parametrize(
        ('severity', 'bucket', 'priority'),
        [
            ('CRITICAL', 'criticalCount', 1),
            ('MAJOR', 'highCount', 2),
            ('MINOR', 'mediumCount', 3),
        ],
    )
    def test_it_should_map_a_severity_to_its_bucket_and_priority(
        self, severity: str, bucket: str, priority: int
    ) -> None:
        findings: list[dict[str, object]] = [
            {'category': 'a', 'file': 'f', 'title': 'A', 'severity': severity, 'task_id': 't1'}
        ]
        output = build_output('security-review', findings, FIXED_NOW)
        assert output[bucket] == 1
        assert output['priorities'] == [priority]
        others = [key for key in ('criticalCount', 'highCount', 'mediumCount') if key != bucket]
        assert [output[key] for key in others] == [0, 0]

    def test_it_should_reject_an_unknown_severity(self, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
        payload = json.dumps([{**FINDING, 'severity': 'BLOCKER'}])
        argv = ['--phase', 'security-review', '--out', str(tmp_path / 'findings.json')]
        assert harden_fingerprint.main(argv, io_module.StringIO(payload), FIXED_NOW) == 1
        assert "unknown severity 'BLOCKER'" in capsys.readouterr().err
        assert not (tmp_path / 'findings.json').exists()


class TestAgentInvocations:
    """The two command lines the sp-*-review agents actually run."""

    def test_it_should_handle_a_findings_file_piped_in(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        # .venv/bin/python -m tools.harden_fingerprint --phase security-review \
        #     < FEATURE_DIR/.sp-findings.json
        findings_file = tmp_path / '.sp-findings.json'
        findings_file.write_text(
            json.dumps([
                {
                    'category': 'injection',
                    'file': 'src/syml/parsers.py',
                    'title': 'Unsafe eval() in the Node visitor!',
                    'severity': 'CRITICAL',
                    'line': 42,
                    'task_id': 'syml-42',
                },
                {
                    'category': 'input-validation',
                    'file': 'src/syml/nodes.py',
                    'title': 'Unbounded recursion depth',
                    'severity': 'MAJOR',
                    'line': None,
                    'task_id': 'syml-43',
                },
            ])
        )
        monkeypatch.chdir(tmp_path)
        with findings_file.open(encoding='utf-8') as stdin:
            assert harden_fingerprint.main(['--phase', 'security-review'], stdin, FIXED_NOW) == 0
        written = json.loads((tmp_path / '.sp-harden-findings.json').read_text())
        assert written == {
            'phase': 'security-review',
            'criticalCount': 1,
            'highCount': 1,
            'mediumCount': 0,
            'taskIds': ['syml-42', 'syml-43'],
            'fingerprints': [
                fingerprint({
                    'category': 'injection',
                    'file': 'src/syml/parsers.py',
                    'title': 'Unsafe eval() in the Node visitor!',
                }),
                fingerprint({
                    'category': 'input-validation',
                    'file': 'src/syml/nodes.py',
                    'title': 'Unbounded recursion depth',
                }),
            ],
            'priorities': [1, 2],
            'timestamp': '2026-09-13T12:00:00+00:00',
        }

    def test_it_should_write_a_clean_review_from_an_empty_array(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # echo '[]' | .venv/bin/python -m tools.harden_fingerprint --phase security-review
        monkeypatch.chdir(tmp_path)
        stdin = io_module.StringIO('[]\n')
        assert harden_fingerprint.main(['--phase', 'security-review'], stdin, FIXED_NOW) == 0
        assert json.loads((tmp_path / '.sp-harden-findings.json').read_text()) == {
            'phase': 'security-review',
            'criticalCount': 0,
            'highCount': 0,
            'mediumCount': 0,
            'taskIds': [],
            'fingerprints': [],
            'priorities': [],
            'timestamp': '2026-09-13T12:00:00+00:00',
        }
