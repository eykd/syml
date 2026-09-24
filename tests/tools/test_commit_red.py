import types

import pytest

from tools import commit_red
from tools.commit_red import (
    HEADER_MAX_LENGTH,
    build_commit_message,
    build_subject,
    is_red_task,
    is_test_file,
    run,
    staged_test_files,
)

RED_TASK: dict[str, object] = {
    'title': 'Red: write failing test for user validation',
    'description': '**Type**: RED (write failing test)',
}


class FakeIo:
    """Recording fake IO whose defaults model the happy path."""

    def __init__(
        self,
        task: dict[str, object] | None = RED_TASK,
        staged: list[str] | None = None,
        *,
        fail: bool = True,
        commit_code: int = 0,
    ) -> None:
        self.task = task
        self.staged = ['tests/test_user.py', 'src/syml/user.py'] if staged is None else staged
        self.fail = fail
        self.commit_code = commit_code
        self.shown: list[str] = []
        self.test_runs: list[list[str]] = []
        self.commits: list[str] = []
        self.outs: list[str] = []
        self.errs: list[str] = []

    def br_show(self, task_id: str) -> dict[str, object] | None:
        self.shown.append(task_id)
        return self.task

    def staged_files(self) -> list[str]:
        return self.staged

    def tests_fail(self, files: list[str]) -> bool:
        self.test_runs.append(files)
        return self.fail

    def git_commit(self, message: str) -> int:
        self.commits.append(message)
        return self.commit_code

    def out(self, message: str) -> None:
        self.outs.append(message)

    def err(self, message: str) -> None:
        self.errs.append(message)


class TestIsRedTask:
    @pytest.mark.parametrize('title', ['RED: do thing', '  red: do thing'])
    def test_it_should_match_a_red_title_prefix(self, title: str) -> None:
        assert is_red_task({'title': title, 'description': ''}) is True

    def test_it_should_match_a_type_red_description_marker(self) -> None:
        assert is_red_task({'title': 'Implement thing', 'description': '**Type**: RED'}) is True

    def test_it_should_reject_non_red_tasks(self) -> None:
        assert is_red_task({'title': 'Green: make it pass', 'description': '**Type**: GREEN'}) is False

    def test_it_should_tolerate_non_string_fields(self) -> None:
        assert is_red_task({'title': None, 'description': 3}) is False


class TestIsTestFile:
    @pytest.mark.parametrize('path', ['tests/test_user.py', 'tests/tools/test_commit_red.py', 'tests/user_test.py'])
    def test_it_should_accept_test_modules(self, path: str) -> None:
        assert is_test_file(path) is True

    @pytest.mark.parametrize('path', ['src/syml/user.py', 'tests/conftest.py', 'tests/test_fixture.json', 'README.md'])
    def test_it_should_reject_non_test_files(self, path: str) -> None:
        assert is_test_file(path) is False


class TestStagedTestFiles:
    def test_it_should_keep_only_test_files_in_order(self) -> None:
        paths = ['src/a.py', 'tests/test_a.py', 'tests/b_test.py', 'README.md']
        assert staged_test_files(paths) == ['tests/test_a.py', 'tests/b_test.py']


class TestBuildSubject:
    def test_it_should_strip_the_red_prefix_and_append_skip_ci(self) -> None:
        subject = build_subject({'title': 'Red: write failing test for X'})
        assert subject == 'test: red — write failing test for X [skip ci]'

    def test_it_should_fall_back_when_the_title_is_only_the_prefix(self) -> None:
        assert build_subject({'title': 'Red:'}) == 'test: red — write failing test [skip ci]'

    def test_it_should_fit_the_header_budget_at_the_boundary(self) -> None:
        assert len(build_subject({'title': 'a' * 78})) == HEADER_MAX_LENGTH

    def test_it_should_exceed_the_budget_one_char_later(self) -> None:
        assert len(build_subject({'title': 'a' * 79})) > HEADER_MAX_LENGTH


class TestBuildCommitMessage:
    def test_it_should_carry_the_id_in_a_refs_footer(self) -> None:
        message = build_commit_message({'title': 'Red: write failing test for X'}, 'syml-1')
        assert message == 'test: red — write failing test for X [skip ci]\n\nRefs: syml-1'


class TestRun:
    def test_it_should_refuse_when_the_task_id_is_missing(self) -> None:
        io = FakeIo()
        assert run([], io) == 1
        assert 'missing required task ID' in io.errs[0]
        assert io.commits == []

    def test_it_should_refuse_when_the_task_id_is_blank(self) -> None:
        io = FakeIo()
        assert run(['   '], io) == 1
        assert 'missing required task ID' in io.errs[0]

    def test_it_should_refuse_when_the_task_does_not_exist(self) -> None:
        io = FakeIo(task=None)
        assert run(['syml-x'], io) == 1
        assert 'not found' in io.errs[0]

    def test_it_should_refuse_a_non_red_task(self) -> None:
        io = FakeIo(task={'title': 'Green: make X pass', 'description': ''})
        assert run(['syml-1'], io) == 1
        assert 'RED TDD task ONLY' in io.errs[0]
        assert 'NOT a way to bypass failing tests' in io.errs[0]
        assert io.commits == []

    def test_it_should_refuse_an_over_long_title_before_any_test_run(self) -> None:
        io = FakeIo(task={'title': f'Red: {'a' * 120}', 'description': '**Type**: RED'})
        assert run(['syml-1'], io) == 1
        assert 'too long' in io.errs[0]
        assert 'br update syml-1' in io.errs[0]
        assert io.test_runs == []
        assert io.commits == []

    def test_it_should_refuse_when_no_test_file_is_staged(self) -> None:
        io = FakeIo(staged=['src/syml/user.py'])
        assert run(['syml-1'], io) == 1
        assert 'no staged test file' in io.errs[0]
        assert io.test_runs == []

    def test_it_should_refuse_when_the_staged_tests_pass(self) -> None:
        io = FakeIo(fail=False)
        assert run(['syml-1'], io) == 1
        assert 'must contain a failing test' in io.errs[0]
        assert io.commits == []

    def test_it_should_run_pytest_against_only_the_staged_test_files(self) -> None:
        io = FakeIo()
        run(['syml-1'], io)
        assert io.test_runs == [['tests/test_user.py']]

    def test_it_should_commit_locally_without_pushing(self) -> None:
        io = FakeIo()
        assert run(['syml-1'], io) == 0
        assert io.commits == ['test: red — write failing test for user validation [skip ci]\n\nRefs: syml-1']
        assert 'Not pushed' in io.outs[0]

    def test_it_should_surface_a_commit_failure(self) -> None:
        io = FakeIo(commit_code=3)
        assert run(['syml-1'], io) == 3
        assert 'NOT a bypass' in io.errs[0]


def fake_completed(returncode: int = 0, stdout: str = '') -> types.SimpleNamespace:
    return types.SimpleNamespace(returncode=returncode, stdout=stdout)


class TestRealIo:
    def test_it_should_parse_a_br_show_object(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr('subprocess.run', lambda *_a, **_k: fake_completed(stdout='{"title": "Red: x"}'))
        assert commit_red.RealIo().br_show('syml-1') == {'title': 'Red: x'}

    def test_it_should_unwrap_a_br_show_array(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr('subprocess.run', lambda *_a, **_k: fake_completed(stdout='[{"title": "Red: x"}]'))
        assert commit_red.RealIo().br_show('syml-1') == {'title': 'Red: x'}

    @pytest.mark.parametrize('stdout', ['[]', '"nope"', 'not json'])
    def test_it_should_return_none_for_unusable_output(self, monkeypatch: pytest.MonkeyPatch, stdout: str) -> None:
        monkeypatch.setattr('subprocess.run', lambda *_a, **_k: fake_completed(stdout=stdout))
        assert commit_red.RealIo().br_show('syml-1') is None

    def test_it_should_return_none_when_br_exits_nonzero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr('subprocess.run', lambda *_a, **_k: fake_completed(returncode=1))
        assert commit_red.RealIo().br_show('syml-1') is None

    def test_it_should_return_none_when_br_is_not_installed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def boom(*_args: object, **_kwargs: object) -> None:
            raise OSError('no br')

        monkeypatch.setattr('subprocess.run', boom)
        assert commit_red.RealIo().br_show('syml-1') is None

    def test_it_should_list_staged_files(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr('subprocess.run', lambda *_a, **_k: fake_completed(stdout='a.py\n\n  b.py  \n'))
        assert commit_red.RealIo().staged_files() == ['a.py', 'b.py']

    @pytest.mark.parametrize('code', [0, 1])
    def test_it_should_report_pytest_failure_from_the_exit_code(
        self, monkeypatch: pytest.MonkeyPatch, code: int
    ) -> None:
        calls: list[list[str]] = []

        def fake_run(args: list[str], **_kwargs: object) -> types.SimpleNamespace:
            calls.append(args)
            return fake_completed(returncode=code)

        monkeypatch.setattr('subprocess.run', fake_run)
        assert commit_red.RealIo().tests_fail(['tests/test_a.py']) is (code != 0)
        assert calls[0][:3] == ['uv', 'run', 'pytest']
        assert '--no-cov' in calls[0]

    def test_it_should_commit_with_only_the_pytest_hook_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        seen_args: list[list[str]] = []
        seen_env: list[dict[str, str]] = []

        def fake_run(args: list[str], *, env: dict[str, str], **_kwargs: object) -> types.SimpleNamespace:
            seen_args.append(args)
            seen_env.append(env)
            return fake_completed(returncode=0)

        monkeypatch.setattr('subprocess.run', fake_run)
        assert commit_red.RealIo().git_commit('test: red — x [skip ci]') == 0
        assert seen_args[0] == ['git', 'commit', '-m', 'test: red — x [skip ci]']
        assert seen_env[0]['SKIP'] == 'pytest-check'
        assert '--no-verify' not in seen_args[0]

    def test_it_should_write_to_stdout_and_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        io = commit_red.RealIo()
        io.out('hello')
        io.err('nope')
        captured = capsys.readouterr()
        assert captured.out == 'hello\n'
        assert captured.err == 'nope\n'


class TestMain:
    def test_it_should_refuse_with_no_arguments(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr('sys.argv', ['commit_red'])
        assert commit_red.main() == 1
        assert 'missing required task ID' in capsys.readouterr().err
