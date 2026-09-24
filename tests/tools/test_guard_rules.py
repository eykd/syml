import pytest

from tools import guard_rules
from tools.guard_rules import Verdict, evaluate_command


def block_id(command: str) -> str | None:
    verdict = evaluate_command(command)
    return None if verdict is None else verdict.rule_id


class TestAllow:
    @pytest.mark.parametrize(
        'command',
        [
            '',
            '   ',
            'uv run pytest',
            'git status',
            'git push',
            'git push origin main',
            'git push -u origin main',
            'git push --force-if-includes',
            'git commit -m "fix: something"',
            'git checkout -b new-feature',
            'git checkout --orphan initial',
            'git checkout feature-branch',
            'git restore --staged tools/foo.py',
            'git restore -S tools/foo.py',
            'git checkout main',
            'git checkout HEAD -- src/x.py',
            'git restore file.py',
            'git restore --staged .',
            'git restore -S .',
            'git clean -n',
            'git clean --dry-run',
            'git clean -fdn',
            'git clean --dry-run -fd',
            'git reset --soft HEAD~1',
            'git branch -d merged-branch',
            'git stash',
            'git stash pop',
            'git stash list',
            'git merge feature',
            'br init',
            'br ready --json',
            'rm -rf node_modules',
            'rm -rf dist',
            'rm -rf build/',
            'rm -rf ./build',
            'rm -f ./notes.txt',
            'gh repo archive',
            'gitcommit --no-verify',
            'echo "dbdb is a word"',
            'git push -n',
            'git commit -m "mention -n in prose"',
            'git commit -am wip',
            'git commit -m x',
        ],
    )
    def test_it_should_allow_safe_commands(self, command: str) -> None:
        assert evaluate_command(command) is None


class TestBlockedRules:
    @pytest.mark.parametrize(
        ('command', 'rule_id'),
        [
            ('git commit --no-verify -m "x"', 'hook-bypass'),
            ('git commit --no-gpg-sign -m "x"', 'hook-bypass'),
            ('git push --no-verify', 'hook-bypass'),
            ('git commit -n -m wip', 'hook-bypass'),
            ('git commit -nm wip', 'hook-bypass'),
            ('git commit -anm wip', 'hook-bypass'),
            ('git -c core.hooksPath=/dev/null commit -m x', 'hook-bypass'),
            ('git -c core.hooksPath=/tmp/none push', 'hook-bypass'),
            ('git push --force origin main', 'force-push'),
            ('git push -f ', 'force-push'),
            ('git push -f', 'force-push'),
            ('git push -uf origin main', 'force-push'),
            ('git push -fu origin main', 'force-push'),
            ('git push --force-with-lease origin feature', 'force-push'),
            ('gh repo delete eykd/syml', 'gh-repo-delete'),
            ('git reset --hard', 'reset-hard'),
            ('git reset --hard origin/main', 'reset-hard'),
            ('git checkout .', 'checkout-dot'),
            ('git checkout -- .', 'checkout-dot'),
            ('git checkout HEAD~1 -- .', 'checkout-treeish-dot'),
            ('git restore .', 'restore-dot'),
            ('git restore . ', 'restore-dot'),
            ('git clean -f', 'clean-force'),
            ('git clean -fd', 'clean-force'),
            ('git clean -xfd', 'clean-force'),
            ('git clean -fd build-gen/', 'clean-force'),
            ('git clean -fd my-plugin/', 'clean-force'),
            ('bd list', 'legacy-bd'),
            ('npx bd list', 'legacy-bd'),
            ('echo hi && bd list', 'legacy-bd'),
            ('br init --force', 'br-init-force'),
            ('br init -f', 'br-init-force'),
            ('git commit --amend -m "fix"', 'commit-amend'),
            ('git merge --squash feature', 'merge-squash'),
            ('git stash drop', 'stash-drop'),
            ('git stash drop stash@{2}', 'stash-drop'),
            ('git stash clear', 'stash-clear'),
            ('git branch -D feature', 'branch-force-delete'),
            ('git branch -Df foo', 'branch-force-delete'),
            ('rm -rf /', 'catastrophic-rm'),
            ('rm -rf .', 'catastrophic-rm'),
            ('rm -fr .', 'catastrophic-rm'),
            ('rm -r -f .', 'catastrophic-rm'),
            ('rm --recursive --force /', 'catastrophic-rm'),
            ('rm --force --recursive /', 'catastrophic-rm'),
            ('rm -rf ~/', 'catastrophic-rm'),
            ('rm -rf ../', 'catastrophic-rm'),
            ('rm -rf ./', 'catastrophic-rm'),
            ('rm -rf $HOME', 'catastrophic-rm'),
            ('rm -rf ${HOME}', 'catastrophic-rm'),
            ('rm -rf *', 'catastrophic-rm'),
            ('rm -Rf /', 'catastrophic-rm'),
            ('rm -fR ~', 'catastrophic-rm'),
            ('rm -rf /*', 'catastrophic-rm'),
            ('rm -rf ./*', 'catastrophic-rm'),
            ('rm -rf ~/*', 'catastrophic-rm'),
            ('rm -rf "$HOME"/*', 'catastrophic-rm'),
            ('rm -rf --no-preserve-root /', 'catastrophic-rm'),
            ('rm -r -f --no-preserve-root /', 'catastrophic-rm'),
        ],
    )
    def test_it_should_block_destructive_commands(self, command: str, rule_id: str) -> None:
        assert block_id(command) == rule_id

    def test_it_should_return_the_rule_message(self) -> None:
        verdict = evaluate_command('git push --force')
        assert isinstance(verdict, Verdict)
        assert 'Force push detected' in verdict.message

    def test_it_should_not_false_positive_on_stash_dropdown(self) -> None:
        assert evaluate_command('git stash dropdown') is None

    def test_it_should_not_false_positive_on_stash_clearfix(self) -> None:
        assert evaluate_command('git stash clearfix') is None


class TestGlobalOptionsAndInterleavedFlags:
    """Regression coverage for syml-x0m.6.6.

    Git global options and interleaved flags between the subcommand and its
    dangerous flag must not bypass a rule.
    """

    @pytest.mark.parametrize(
        ('command', 'rule_id'),
        [
            ('git -C . reset --hard', 'reset-hard'),
            ('git -c x=y reset --hard', 'reset-hard'),
            ('git reset -q --hard', 'reset-hard'),
            ('git reset HEAD --hard', 'reset-hard'),
            ('git -C . push --force', 'force-push'),
            ('git push origin +main', 'force-push'),
            ('git -C . clean -fd', 'clean-force'),
            ('git -C . branch -D foo', 'branch-force-delete'),
            ('git "-C" . reset --hard', 'reset-hard'),
        ],
    )
    def test_it_should_block_global_options_and_interleaved_flags(self, command: str, rule_id: str) -> None:
        assert block_id(command) == rule_id

    @pytest.mark.parametrize(
        'command',
        [
            'git -C . status',
            'git -c user.name=x log',
            'git reset --soft HEAD~1',
            'git push',
            'git checkout -- file.py',
            'git push && date +%s',
            'git push origin main && echo "+1"',
        ],
    )
    def test_it_should_still_allow_safe_commands_with_global_options(self, command: str) -> None:
        assert evaluate_command(command) is None


class TestInterveningTreeishOrOptionBeforeDotTarget:
    """Regression coverage for syml-x0m.6.9.

    An intervening tree-ish or option between the subcommand and a
    standalone "." target must not bypass the checkout/restore discard
    guard rules.
    """

    @pytest.mark.parametrize(
        ('command', 'rule_id'),
        [
            ('git checkout HEAD .', 'checkout-treeish-dot'),
            ('git checkout -f HEAD .', 'checkout-treeish-dot'),
            ('git restore --worktree .', 'restore-dot'),
            ('git restore -W .', 'restore-dot'),
            ('git restore --source=HEAD .', 'restore-dot'),
            ('git restore --staged --worktree .', 'restore-dot'),
        ],
    )
    def test_it_should_block_intervening_tokens_before_a_dot_target(self, command: str, rule_id: str) -> None:
        assert block_id(command) == rule_id

    @pytest.mark.parametrize(
        'command',
        [
            'git checkout main',
            'git checkout -- file.py',
            'git checkout HEAD -- src/x.py',
            'git restore file.py',
            'git restore --staged .',
            'git restore -S .',
        ],
    )
    def test_it_should_still_allow_safe_commands(self, command: str) -> None:
        assert evaluate_command(command) is None


class TestQuoteBypass:
    """Regression coverage for syml-x0m.6.3: quoting must not bypass a rule."""

    @pytest.mark.parametrize(
        ('command', 'rule_id'),
        [
            ('git reset "--hard"', 'reset-hard'),
            ("git reset '--hard'", 'reset-hard'),
            ('git reset --ha""rd', 'reset-hard'),
            ('git commit "--am""end" -m x', 'commit-amend'),
            ('git clean "-fd"', 'clean-force'),
            ('git branch "-D" foo', 'branch-force-delete'),
            ('git stash "drop"', 'stash-drop'),
            ('git checkout "."', 'checkout-dot'),
            ('rm -rf "/"', 'catastrophic-rm'),
        ],
    )
    def test_it_should_block_quoted_and_split_quoted_dangerous_tokens(self, command: str, rule_id: str) -> None:
        assert block_id(command) == rule_id

    @pytest.mark.parametrize(
        'command',
        [
            'git commit -m "do not --amend"',
            'git commit -am "do not --amend"',
            'git commit --message "do not --amend"',
            'git commit --message="do not --amend"',
        ],
    )
    def test_it_should_still_allow_a_commit_message_mentioning_a_dangerous_phrase(self, command: str) -> None:
        assert evaluate_command(command) is None

    def test_it_should_fail_closed_on_unbalanced_quotes(self) -> None:
        assert block_id('git branch "-D') == 'branch-force-delete'

    def test_it_should_drop_a_message_flag_value_at_the_end_of_the_command(self) -> None:
        assert evaluate_command('git commit -m') is None

    def test_it_should_dequote_and_split_shell_separated_subcommands(self) -> None:
        assert block_id('echo hi && git reset "--hard"') == 'reset-hard'

    def test_it_should_skip_empty_groups_between_repeated_separators(self) -> None:
        assert guard_rules.dequote_subcommands('a && && b') == ['a', 'b']

    def test_it_should_drop_a_trailing_separator_with_no_trailing_group(self) -> None:
        assert guard_rules.dequote_subcommands('a &&') == ['a']


class TestStripOrdering:
    def test_it_should_block_a_bypass_flag_hidden_in_quotes(self) -> None:
        assert block_id('git commit -m "use --no-verify never"') == 'hook-bypass'

    def test_it_should_allow_a_post_strip_pattern_inside_quotes(self) -> None:
        assert evaluate_command('git commit -m "do not --amend"') is None

    def test_it_should_allow_legacy_bd_inside_quotes(self) -> None:
        assert evaluate_command("echo 'bd list'") is None

    def test_it_should_evaluate_sub_commands_independently(self) -> None:
        assert block_id('git clean -n && git clean -f') == 'clean-force'


class TestQuotedProgramOrSubcommandBypass:
    """Regression coverage for syml-x0m.6.4: quoting the program or subcommand

    word must not bypass PRE_STRIP_RULES or PLATFORM_RULES.
    """

    @pytest.mark.parametrize(
        ('command', 'rule_id'),
        [
            ('"git" commit --no-verify -m x', 'hook-bypass'),
            ("'git' push --force", 'force-push'),
            ('git "push" --force', 'force-push'),
            ('"gh" repo delete x', 'gh-repo-delete'),
            ('gh "repo" delete x', 'gh-repo-delete'),
        ],
    )
    def test_it_should_block_quoted_program_or_subcommand_words(self, command: str, rule_id: str) -> None:
        assert block_id(command) == rule_id

    def test_it_should_still_allow_a_commit_message_mentioning_a_dangerous_phrase(self) -> None:
        assert evaluate_command('git commit -m "do not --amend"') is None


class TestNormalizeCommand:
    def test_it_should_collapse_line_continuations(self) -> None:
        assert guard_rules.normalize_command('git push \\\n  --force') == 'git push  --force'

    def test_it_should_strip_a_leading_backslash(self) -> None:
        assert guard_rules.normalize_command('\\rm -rf /') == 'rm -rf /'

    def test_it_should_strip_chained_wrappers(self) -> None:
        assert guard_rules.normalize_command('sudo nice env FOO=1 rm -rf /') == 'rm -rf /'

    def test_it_should_block_a_wrapped_destructive_command(self) -> None:
        assert block_id('sudo rm -rf /') == 'catastrophic-rm'


class TestStripQuotedContent:
    def test_it_should_strip_a_heredoc(self) -> None:
        text = "cat <<'EOF'\nrm -rf /\nEOF"
        assert 'rm -rf' not in guard_rules.strip_quoted_content(text)

    def test_it_should_keep_escaped_quotes_inside_double_quotes(self) -> None:
        assert guard_rules.strip_quoted_content(r'echo "a \" b"') == 'echo ""'


class TestSplitCommands:
    @pytest.mark.parametrize(
        ('command', 'expected'),
        [
            ('a && b', ['a', 'b']),
            ('a || b', ['a', 'b']),
            ('a ; b', ['a', 'b']),
            ('a | b', ['a', 'b']),
            ('', []),
        ],
    )
    def test_it_should_split_on_shell_separators(self, command: str, expected: list[str]) -> None:
        assert guard_rules.split_commands(command) == expected


class TestCommandSubstitutionInMessagePayload:
    """Regression coverage for syml-x0m.6.5: command substitution inside a

    commit/tag message payload must not escape guard rules, since the shell
    evaluates it before git ever runs.
    """

    @pytest.mark.parametrize(
        ('command', 'rule_id'),
        [
            ('git commit -m "$(git reset --hard)"', 'reset-hard'),
            ('git commit -m "`git reset --hard`"', 'reset-hard'),
            ('git commit --message="$(git reset --hard)"', 'reset-hard'),
            ('git commit -m "$(rm -rf /)"', 'catastrophic-rm'),
            ('git tag -m "$(git reset --hard)" v1', 'reset-hard'),
        ],
    )
    def test_it_should_block_a_command_substitution_hidden_in_a_message(self, command: str, rule_id: str) -> None:
        assert block_id(command) == rule_id

    def test_it_should_still_allow_a_plain_message_mentioning_a_dangerous_phrase(self) -> None:
        assert evaluate_command('git commit -m "docs: explain git reset --hard"') is None


class TestShellWrappers:
    def test_it_should_unwrap_a_single_quoted_bash_payload(self) -> None:
        assert block_id("bash -c 'rm -rf /'") == 'catastrophic-rm'

    def test_it_should_unwrap_a_double_quoted_bash_payload(self) -> None:
        assert block_id('bash -c "rm -rf /"') == 'catastrophic-rm'

    def test_it_should_unwrap_an_unquoted_eval_payload(self) -> None:
        assert block_id('eval rm -rf /') == 'catastrophic-rm'

    def test_it_should_unwrap_an_unterminated_double_quoted_payload(self) -> None:
        assert block_id('bash -c "rm -rf /') == 'catastrophic-rm'

    def test_it_should_unwrap_an_unterminated_single_quoted_payload(self) -> None:
        assert block_id("bash -c 'rm -rf /") == 'catastrophic-rm'

    def test_it_should_honour_escapes_in_a_double_quoted_payload(self) -> None:
        assert block_id('bash -c "echo \\"hi\\" && rm -rf /"') == 'catastrophic-rm'

    def test_it_should_allow_a_safe_wrapped_payload(self) -> None:
        assert evaluate_command("bash -c 'uv run pytest'") is None

    def test_it_should_allow_an_empty_payload(self) -> None:
        assert evaluate_command('bash -c ') is None

    def test_it_should_stop_unwrapping_past_the_depth_limit(self) -> None:
        # The third level is never unwrapped; only its literal text is scanned.
        assert evaluate_command('bash -c "bash -c \'bash -c whoami\'"') is None
