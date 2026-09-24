"""Bindings for specs/acceptance-specs/US09-release-readiness.feature."""

from __future__ import annotations

import importlib
import importlib.metadata
import subprocess  # noqa: S404
import sys
import warnings
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when

pytestmark = pytest.mark.acceptance

scenarios('US09-release-readiness.feature')

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@given('the repository at the end of this feature', target_fixture='repo_root')
def given_repo(context: dict[str, Any]) -> Path:
    return _REPO_ROOT


@given('the repository', target_fixture='repo_root')
def given_repo_plain(context: dict[str, Any]) -> Path:
    return _REPO_ROOT


@given('SYML-SPECIFICATION.md', target_fixture='spec_text')
def given_spec() -> str:
    return (_REPO_ROOT / 'SYML-SPECIFICATION.md').read_text(encoding='utf-8')


@given('the migration notes', target_fixture='changelog_text')
def given_migration_notes() -> str:
    return (_REPO_ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')


@given('a fresh environment')
def given_fresh_environment() -> None:
    """No setup needed: importing syml in a subprocess is a fresh interpreter."""


@given('the node-tree test module', target_fixture='node_tree_test_text')
def given_node_tree_test_module() -> str:
    return (_REPO_ROOT / 'tests' / 'test_nodes.py').read_text(encoding='utf-8')


@given("the plan's Constitution Check section", target_fixture='plan_text')
def given_plan() -> str:
    plan_path = _REPO_ROOT / 'specs' / '001-syml-1-0-conformance' / 'plan.md'
    return plan_path.read_text(encoding='utf-8')


@given('the constitution', target_fixture='constitution_text')
def given_constitution() -> str:
    return (_REPO_ROOT / '.specify' / 'memory' / 'constitution.md').read_text(encoding='utf-8')


@when('the project version metadata is read', target_fixture='project_version')
def when_project_version_read() -> str:
    return importlib.metadata.version('syml')


@then('it declares "1.0.0"')
def then_version_is_1_0_0(project_version: str) -> None:
    assert project_version == '1.0.0'


@when('its header is read', target_fixture='spec_header')
def when_spec_header_read(spec_text: str) -> str:
    return '\n'.join(spec_text.splitlines()[:10])


@then('it is labelled version 1.0 and names syml 1.0.0 as the conforming ' 'reference implementation')
def then_spec_header_labelled(spec_header: str) -> None:
    assert '**Version:** 1.0' in spec_header
    assert '(1.0.0)' in spec_header
    assert 'conforming reference implementation' in spec_header


@then('the review pass and the release are folded into a single version-history entry')
def then_version_history_folded(spec_text: str) -> None:
    version_history_index = spec_text.index('## 14')
    version_history = spec_text[version_history_index:]
    assert version_history.count('| 1.1 |') == 0
    assert version_history.count('1.0') >= 1


@when('a 0.6.2 user reads them', target_fixture='migration_notes_read')
def when_migration_notes_read(changelog_text: str) -> str:
    return changelog_text


@then(
    'they list the null-to-empty-string change, tabs and duplicate keys '
    'becoming errors, quoted values decoding, the leading-marker and '
    'key-colon-value fallthrough, third-party parser exceptions no longer '
    'escaping, the new load input types, and the new dumps and dump'
)
def then_migration_notes_list_changes(migration_notes_read: str) -> None:
    text = migration_notes_read.lower()
    expected_fragments = [
        'none',  # null-to-empty-string change
        'tab',
        'duplicatekeyerror',
        'quoted',
        'fallthrough',
        'parsimonious',
        'load',
        'dumps',
        'dump',
    ]
    for fragment in expected_fragments:
        assert fragment in text, f'expected migration notes to mention {fragment!r}'


@when('it is searched for a conformance ledger', target_fixture='conformance_search')
def when_searched_for_conformance_ledger(repo_root: Path) -> dict[str, Any]:
    claude_md = (repo_root / 'CLAUDE.md').read_text(encoding='utf-8')
    return {
        'todo_txt_exists': (repo_root / 'todo.txt').exists(),
        'claude_md': claude_md,
    }


@then(
    'todo.txt is retired or rewritten with no conformance claim, and '
    'CLAUDE.md\'s "Spec vs. implementation" section says the parser conforms'
)
def then_one_conformance_ledger(conformance_search: dict[str, Any]) -> None:
    assert conformance_search['todo_txt_exists'] is False
    claude_md = conformance_search['claude_md']
    assert 'Spec vs. implementation' in claude_md
    section_index = claude_md.index('Spec vs. implementation')
    section = claude_md[section_index:]
    assert 'conforming reference implementation' in section


@when('syml is imported')
def when_syml_imported() -> None:
    result = subprocess.run(  # noqa: S603
        [sys.executable, '-W', 'error', '-c', 'import syml'],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@then('no warning is emitted')
def then_no_warning_emitted() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        importlib.reload(importlib.import_module('syml'))


@when('it is inspected', target_fixture='node_tree_inspection')
def when_node_tree_inspected(node_tree_test_text: str) -> dict[str, Any]:
    basetypes_text = (_REPO_ROOT / 'src' / 'syml' / 'basetypes.py').read_text(encoding='utf-8')
    return {'test_text': node_tree_test_text, 'basetypes_text': basetypes_text}


@then(
    'it holds real tests rather than being empty, and the dead statement ' "in Source's concatenation operator is gone"
)
def then_node_tree_has_real_tests(node_tree_inspection: dict[str, Any]) -> None:
    test_text = node_tree_inspection['test_text']
    assert test_text.strip() != ''
    assert 'def test_' in test_text
    basetypes_text = node_tree_inspection['basetypes_text']
    add_index = basetypes_text.index('def __add__')
    add_body = basetypes_text[add_index : add_index + 800]
    assert 'pass' not in add_body.split('\n\n')[0].split('\n')[1:]


@when('principle IV is read', target_fixture='principle_iv_text')
def when_principle_iv_read(constitution_text: str) -> str:
    start = constitution_text.index('### IV. Spec vs Implementation Discipline')
    end = constitution_text.index('###', start + 1)
    return constitution_text[start:end]


@then('it no longer claims the specification is aspirational or that todo.txt is the conformance ledger')
def then_principle_iv_no_stale_claims(principle_iv_text: str) -> None:
    lowered = principle_iv_text.lower()
    assert 'aspirational' not in lowered
    assert 'todo.txt' not in lowered or 'ledger' not in lowered


@then('it permits a specification edit that lands in the same commit as the behavior change it exposed')
def then_principle_iv_permits_spec_edit(principle_iv_text: str) -> None:
    assert 'same commit' in principle_iv_text


@then('the constitution version is bumped per its own Governance Amendment Procedure and Versioning Policy')
def then_constitution_version_bumped(constitution_text: str) -> None:
    assert '2.0.0' in constitution_text[:2000]


@when('it is read', target_fixture='constitution_check_section')
def when_constitution_check_section_read(plan_text: str) -> str:
    start = plan_text.index('## Constitution Check')
    return plan_text[start:]


@then(
    'it lists Pos moving to original-text coordinates, load accepting '
    'binary streams, and the resulting 1.0.0 major version bump, each '
    'paired with the non-breaking alternative it rejected'
)
def then_constitution_check_lists_breaks(constitution_check_section: str) -> None:
    assert 'original-text coordinates' in constitution_check_section
    assert 'binary streams' in constitution_check_section or 'IO[bytes]' in constitution_check_section
    assert '1.0.0' in constitution_check_section
    assert 'rejected' in constitution_check_section.lower()


@when('it is inspected for release artifacts', target_fixture='release_artifacts')
def when_inspected_for_release_artifacts(repo_root: Path) -> dict[str, Any]:
    tags = subprocess.run(  # noqa: S603
        ['git', 'tag', '--list'],  # noqa: S607
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    dist_dir = repo_root / 'dist'
    dist_files = list(dist_dir.glob('*')) if dist_dir.exists() else []
    return {'tags': tags, 'dist_files': dist_files}


@then('no 1.0.0 tag exists and no distribution has been built or uploaded')
def then_no_release_artifacts(release_artifacts: dict[str, Any]) -> None:
    assert '1.0.0' not in release_artifacts['tags']
    assert release_artifacts['dist_files'] == []
