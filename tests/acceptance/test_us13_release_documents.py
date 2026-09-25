"""Bindings for specs/acceptance-specs/US13-release-documents.feature."""

from __future__ import annotations

import re
import subprocess  # noqa: S404
import sys
from pathlib import Path

import pytest
from parsimonious import Grammar
from pytest_bdd import given, scenarios, then, when

import syml
from syml import parsers

pytestmark = pytest.mark.acceptance

scenarios('US13-release-documents.feature')

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# --- Scenario: Every specification example produces exactly its stated output ---


@given('the revised SYML-SPECIFICATION.md', target_fixture='spec_examples_run')
def given_revised_spec() -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, '-m', 'pytest', 'tests/test_spec_examples.py', '--no-cov', '-q'],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


@when('every fenced syml block that states an Output or an ERROR is run')
def when_spec_examples_run() -> None:
    """The subprocess in the Given step already ran every example."""


@then('each produces exactly that output or raises exactly that error')
def then_spec_examples_pass(spec_examples_run: subprocess.CompletedProcess[str]) -> None:
    assert spec_examples_run.returncode == 0, spec_examples_run.stdout + spec_examples_run.stderr
    assert 'xfailed' not in spec_examples_run.stdout


# --- Scenario: The printed grammar matches the grammar the parser declares ---


@given('the grammar printed in specification section 4.1', target_fixture='spec_grammar')
def given_printed_grammar() -> Grammar:
    spec_text = (_REPO_ROOT / 'SYML-SPECIFICATION.md').read_text(encoding='utf-8')
    match = re.search(r'```peg\n(.*?)```', spec_text, re.DOTALL)
    assert match is not None, 'SYML-SPECIFICATION.md must have a fenced ```peg block in §4.1'
    return Grammar(match.group(1))


@when('it is compared with the grammar the parser declares', target_fixture='grammar_comparison')
def when_grammar_compared(spec_grammar: Grammar) -> tuple[Grammar, Grammar]:
    return spec_grammar, parsers.SymlParser.grammar


@then('the two are the same rule set')
def then_grammars_match(grammar_comparison: tuple[Grammar, Grammar]) -> None:
    spec_grammar, code_grammar = grammar_comparison
    spec_rules = {name: rule.as_rule() for name, rule in spec_grammar.items()}
    code_rules = {name: rule.as_rule() for name, rule in code_grammar.items()}
    assert spec_rules == code_rules
    assert spec_grammar.default_rule.name == 'document'
    assert code_grammar.default_rule.name == 'document'


# --- Shared "it is read" step: SYML-SPEC-REVIEW.md and README.md scenarios ---


@given('SYML-SPEC-REVIEW.md', target_fixture='doc_text')
def given_spec_review() -> str:
    return (_REPO_ROOT / 'SYML-SPEC-REVIEW.md').read_text(encoding='utf-8')


@given('the README', target_fixture='doc_text')
def given_the_readme() -> str:
    return (_REPO_ROOT / 'README.md').read_text(encoding='utf-8')


@when('it is read', target_fixture='doc_text')
def when_doc_read(doc_text: str) -> str:
    return doc_text


@then(
    'decisions D20 through D25 record the key pattern, text context, paragraph breaks, '
    'column-0-only comments, tab as separator, and strict indentation, each with the '
    'alternative not taken and a breaking-change note'
)
def then_review_records_d20_through_d25(doc_text: str) -> None:
    for decision in ('D20', 'D21', 'D22', 'D23', 'D24', 'D25'):
        start = doc_text.index(f'| {decision} |')
        row = doc_text[start : doc_text.index('\n', start)]
        assert 'Breaking change' in row or 'breaking change' in row.lower() or 'Supersedes' in row


@then('decisions D5, D12, D13, D15, and D19 are annotated in place as superseded')
def then_old_decisions_annotated_superseded(doc_text: str) -> None:
    for decision, superseder in (
        ('D5', 'D24'),
        ('D12', 'D22'),
        ('D13', 'D21'),
        ('D15', 'D20'),
        ('D19', 'D20'),
    ):
        start = doc_text.index(f'| {decision} |')
        row = doc_text[start : doc_text.index('\n', start)]
        assert f'Superseded by {superseder}' in row


@then(
    'a "Coming from YAML" section lists, in order, comments only at column 0, '
    'no block-scalar indicators, no document markers, no quoting, that '
    'null/true/123/tilde/lists/mappings written inline are plain strings, the key pattern, '
    'that a key or list marker needs a space after it, the sibling-column rule, paragraph breaks, '
    'and that trailing whitespace is kept and over-indented lines join the value above'
)
def then_readme_lists_coming_from_yaml_in_order(doc_text: str) -> None:
    heading_index = doc_text.index('Coming from YAML')
    section = doc_text[heading_index:]
    phrases = [
        'column 0',
        'block-scalar',
        'document markers',
        'quoting',
        'plain strings',
        r'\[a-z\]\[a-z0-9_-\]\*',
        'needs a space after it',
        'sibling column',
        'paragraph break',
        'Trailing whitespace',
    ]
    positions = [_index_of(section, phrase) for phrase in phrases]
    assert positions == sorted(positions), f'expected {phrases} in order, got indices {positions}'


def _index_of(text: str, pattern: str) -> int:
    match = re.search(pattern, text)
    assert match is not None, f'expected to find {pattern!r} in the "Coming from YAML" section'
    return match.start()


# --- Scenario: The changelog's 1.0.0 entry describes what master does ---


@given("CHANGELOG.md's 1.0.0 entry", target_fixture='changelog_text')
def given_changelog_entry() -> str:
    return (_REPO_ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')


@when('it is read by a 0.6.2 user', target_fixture='changelog_text')
def when_changelog_read(changelog_text: str) -> str:
    return changelog_text


@then('items 4, 7, 10, 12, 13, 16, and 17 describe what master does')
def then_changelog_items_describe_master(changelog_text: str) -> None:
    # Item 4 (D20 key pattern): no stale General_Category wording.
    assert 'General_Category' not in changelog_text
    assert '[a-z][a-z0-9_-]*' in changelog_text
    # Item 10: the real Source.from_node signature.
    assert (
        'from_node` takes\n    `(pnode, filename=None)`' in changelog_text
        or '`(pnode, filename=None)`' in changelog_text
    )
    # Item 13: measured recursion figures, not the old ~500/~1000 placeholders.
    assert 'Measured at' in changelog_text
    # Item 16: stale claims removed.
    assert 'doc` argument' not in changelog_text
    assert 'KeyLeafNode.key` is removed' not in changelog_text
    # Item 17 / D25: indentless sequences.
    assert 'indentless sequence' in changelog_text.lower()


@then(
    'new items state the column-0-only comment rule, the key pattern, that values are text '
    'throughout, that blank lines inside values are kept, that indentless sequences are '
    'rejected, and that a tab after a marker is separator whitespace'
)
def then_changelog_states_new_items(changelog_text: str) -> None:
    lowered = changelog_text.lower()
    for fragment in (
        'column-0 only',
        '[a-z][a-z0-9_-]*',
        'text throughout',
        'paragraph break',
        'indentless sequence',
        'separator whitespace',
    ):
        assert fragment.lower() in lowered, f'expected CHANGELOG.md to mention {fragment!r}'


# --- Scenario: Every documented exception class is exported ---


@given('specification section 11.3', target_fixture='section_11_3_classes')
def given_section_11_3() -> list[str]:
    text = (_REPO_ROOT / 'SYML-SPECIFICATION.md').read_text(encoding='utf-8')
    start = text.index('### 11.3 Exceptions')
    block_start = text.index('```\n', start) + len('```\n')
    block_end = text.index('\n```', block_start)
    block = text[block_start:block_end]
    class_header_re = re.compile(r'^([A-Za-z]+)\(([A-Za-z]+)\)$', re.MULTILINE)
    return [name for name, _base in class_header_re.findall(block)]


@when("it is compared with the package's exports", target_fixture='section_11_3_classes')
def when_compared_with_exports(section_11_3_classes: list[str]) -> list[str]:
    return section_11_3_classes


@then('every class the spec says MUST exist is exported')
def then_every_required_class_is_exported(section_11_3_classes: list[str]) -> None:
    # `DocumentLimitError` is reserved in §11.3's closing prose, below the
    # "MUST expose these exact class names" sentence, so it never appears in
    # the fenced class block `section_11_3_classes` is drawn from.
    assert section_11_3_classes
    for name in section_11_3_classes:
        assert name in syml.__all__, f'{name} is documented in §11.3 but missing from syml.__all__'


@then('every exported error class is listed')
def then_every_exported_error_class_is_listed(section_11_3_classes: list[str]) -> None:
    exported_errors = [name for name in syml.__all__ if name.endswith('Error')]
    for name in exported_errors:
        assert name in section_11_3_classes, f'syml.{name} is exported but not documented in §11.3'


# --- Scenario: The 1.0.0 tag is pushed to the remote (@release, stays red until tagged) ---


@given('the release')
def given_the_release() -> None:
    """No setup: the When step queries the remote directly."""


@when('git ls-remote --tags origin is run', target_fixture='tag_refs')
def when_ls_remote_tags_run() -> dict[str, str]:
    result = subprocess.run(  # noqa: S603
        ['git', 'ls-remote', '--tags', 'origin'],  # noqa: S607
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    refs: dict[str, str] = {}
    for line in result.stdout.splitlines():
        sha, ref = line.split('\t')
        refs[ref] = sha
    return refs


@then('1.0.0 is present and points at the commit that carries the revised spec, code, ' 'changelog, and README')
def then_tag_points_at_release_commit(tag_refs: dict[str, str]) -> None:
    peeled_ref = 'refs/tags/1.0.0^{}'
    assert peeled_ref in tag_refs, '1.0.0 tag is not yet pushed to origin'
    peeled_sha = tag_refs[peeled_ref]
    tag_commit = subprocess.run(  # noqa: S603
        ['git', 'rev-parse', '1.0.0^{commit}'],  # noqa: S607
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert peeled_sha == tag_commit
    merge_base = subprocess.run(  # noqa: S603
        ['git', 'merge-base', '--is-ancestor', tag_commit, 'HEAD'],  # noqa: S607
        cwd=_REPO_ROOT,
        check=False,
    )
    assert (
        merge_base.returncode == 0
        or tag_commit
        == subprocess.run(  # noqa: S603
            ['git', 'rev-parse', 'HEAD'],  # noqa: S607
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )


# --- Scenario: The public docs for Source state its semantics ---


@given('the public docs for Source', target_fixture='source_docs_text')
def given_source_docs() -> str:
    return (_REPO_ROOT / 'README.md').read_text(encoding='utf-8')


@when('they are read', target_fixture='source_docs_text')
def when_source_docs_read(source_docs_text: str) -> str:
    return source_docs_text


@then(
    'they state that Source is not a str, that an empty Source is truthy, and that a '
    'multi-line Source.text is the dedented value as_data returns'
)
def then_source_docs_state_semantics(source_docs_text: str) -> None:
    section_index = source_docs_text.index('`Source`')
    section = source_docs_text[section_index:]
    assert 'not a `str`' in section or 'not a str' in section
    assert 'truthy' in section
    assert 'as_data()' in section
