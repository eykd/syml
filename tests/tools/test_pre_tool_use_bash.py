import io as io_module
import json

import pytest

from tools import pre_tool_use_bash


def feed(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setattr('sys.stdin', io_module.StringIO(raw))


class TestExtractCommand:
    def test_it_should_extract_a_command(self) -> None:
        raw = json.dumps({'tool_input': {'command': 'git status'}})
        assert pre_tool_use_bash.extract_command(raw) == 'git status'

    @pytest.mark.parametrize(
        'raw',
        [
            '',
            'not json',
            '[]',
            '{}',
            '{"tool_input": "nope"}',
            '{"tool_input": {}}',
            '{"tool_input": {"command": 3}}',
        ],
    )
    def test_it_should_return_none_for_unusable_payloads(self, raw: str) -> None:
        assert pre_tool_use_bash.extract_command(raw) is None


class TestMain:
    def test_it_should_allow_a_safe_command(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        feed(monkeypatch, json.dumps({'tool_input': {'command': 'git status'}}))
        assert pre_tool_use_bash.main() == 0
        assert capsys.readouterr().err == ''

    def test_it_should_block_a_destructive_command(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        feed(monkeypatch, json.dumps({'tool_input': {'command': 'git push --force origin main'}}))
        assert pre_tool_use_bash.main() == 2
        assert 'Force push detected' in capsys.readouterr().err

    def test_it_should_fail_open_on_malformed_input(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        feed(monkeypatch, 'not json at all')
        assert pre_tool_use_bash.main() == 0
        assert 'allowing' in capsys.readouterr().err
