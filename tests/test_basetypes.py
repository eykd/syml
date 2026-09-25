import gc
import importlib
import re
import textwrap
import tracemalloc
from typing import cast
from unittest import mock

import pytest

import syml
from syml import basetypes, parsers
from syml.nodes import KeyValue


class TestSource:
    def test_it_should_work_interchangeably_as_a_dict_key_with_comparable_string(self) -> None:
        text = 'foo'
        source = basetypes.Source.from_text(text, 'foo')
        data = {source: 'bar'}
        assert data['foo'] == 'bar'  # type: ignore[index]

    def test_it_should_represent_itself_nicely(self) -> None:
        text = textwrap.dedent(
            """
            - foo
            - bar
            - baz
        """
        )
        source = basetypes.Source.from_text(text, 'foo', filename='foo.txt')
        assert source == basetypes.Source(
            filename='foo.txt',
            start=basetypes.Pos(index=3, line=2, column=2),
            end=basetypes.Pos(index=6, line=2, column=5),
            text='foo',
        )
        assert repr(source) == "<Source: foo.txt, Line 2, Column 2 (index 3): 'foo'>"

    def test_it_should_add_more_text(self) -> None:
        text = textwrap.dedent(
            """
            - foo
            - bar
              baz
        """
        )
        source = basetypes.Source.from_text(text, 'foo', filename='foo.txt')
        new_source = source + '  baz'
        assert new_source is not source
        assert new_source == basetypes.Source(
            filename='foo.txt',
            start=basetypes.Pos(index=3, line=2, column=2),
            end=basetypes.Pos(index=11, line=3, column=5),
            text='foo\n  baz',
        )

    def test_it_should_add_more_source(self) -> None:
        text = textwrap.dedent(
            """
            - foo
            - bar
              baz
            """
        )
        source = basetypes.Source.from_text(text, 'foo', filename='foo.txt')
        source_2 = basetypes.Source.from_text(text, 'baz', filename='foo.txt')
        new_source = source + source_2
        assert new_source is not source
        assert new_source == basetypes.Source(
            filename='foo.txt',
            start=basetypes.Pos(index=3, line=2, column=2),
            end=basetypes.Pos(index=18, line=4, column=5),
            text='foo\nbaz',
        )

    def test_it_should_fail_on_no_substring_match(self) -> None:
        with pytest.raises(ValueError):  # noqa: PT011
            basetypes.Source.from_text('foo', 'bar', filename='blah.txt')

    def test_it_should_fail_to_add_non_source_type(self) -> None:
        source = basetypes.Source.from_text('foo', 'foo', filename='blah.txt')
        with pytest.raises(TypeError):
            source + 5  # type: ignore[operator]

    def test_add_str_end_index_counts_the_joining_newline(self) -> None:
        r"""Contract 08 §Source.__add__ (pass 20).

        `Source.__eq__` compares by text alone, so the existing `+ '  baz'`
        test above cannot catch a wrong `end`. Assert `.end` directly: the
        joining `\n` inserted between `self.text` and `other` must be
        counted in `end.index`, and line/column counting must go through
        `str.split('\n')`, never `str.splitlines()`.
        """
        source = basetypes.Source(
            filename='foo.txt',
            start=basetypes.Pos(index=0, line=1, column=0),
            end=basetypes.Pos(index=3, line=1, column=3),
            text='foo',
        )

        new_source = source + 'bar'

        # 3 (existing text) + 1 (joining '\n') + 3 ('bar') = 7
        assert new_source.end == basetypes.Pos(index=7, line=2, column=3)

    def test_add_str_splits_on_lf_only_not_unicode_line_separators(self) -> None:
        """A Unicode line separator (U+2028) in `other` must not be counted as a line break."""
        source = basetypes.Source(
            filename='foo.txt',
            start=basetypes.Pos(index=0, line=1, column=0),
            end=basetypes.Pos(index=3, line=1, column=3),
            text='foo',
        )

        other = 'a\u2028b'
        new_source = source + other

        assert new_source.end == basetypes.Pos(index=len('foo') + 1 + len(other), line=2, column=3)

    def test_add_empty_str_does_not_raise(self) -> None:
        r"""`splitlines('')` returns `[]`, so the old `lines[-1]` raised `IndexError`.

        `''.split('\n')` returns `['']`, so `Source + ''` is a valid, empty
        continuation line: one joining `\n` and no characters after it.
        """
        source = basetypes.Source(
            filename='foo.txt',
            start=basetypes.Pos(index=0, line=1, column=0),
            end=basetypes.Pos(index=3, line=1, column=3),
            text='foo',
        )

        new_source = source + ''

        assert new_source.end == basetypes.Pos(index=4, line=2, column=0)

    def test_it_should_not_equal_non_str_operands_by_stringified_value(self) -> None:
        """Contract 08 §Equality and hashing (§10.3, R-07).

        `__eq__` must compare with `str`s and `Source`s only, returning
        `NotImplemented` for any other type instead of falling back to
        `str(self) == str(other)`. A `Source('1')` must not equal the `int`
        `1`, even though `str(1) == '1'`.
        """
        source = basetypes.Source.from_text('1', '1')
        assert source != 1
        assert 1 != source  # noqa: SIM300


class TestPosFromStrIndex:
    @pytest.fixture
    def text(self) -> str:
        return textwrap.dedent(
            """

            foo
                bar
                    baz blah blargh
            boo
            """
        )

    def test_returns_line_and_column_at_start_of_line(self, text: str) -> None:
        match = re.search('foo', text)
        start = match.start()  # type: ignore[union-attr]
        assert basetypes.Pos.from_str_index(text, start) == basetypes.Pos(start, 3, 0)

    def test_returns_line_and_column_of_indented_text(self, text: str) -> None:
        match = re.search('bar', text)
        start = match.start()  # type: ignore[union-attr]
        assert basetypes.Pos.from_str_index(text, start) == basetypes.Pos(start, 4, 4)

    def test_returns_line_and_column_of_midline_text(self, text: str) -> None:
        match = re.search('blah', text)
        start = match.start()  # type: ignore[union-attr]
        assert basetypes.Pos.from_str_index(text, start) == basetypes.Pos(start, 5, 12)

    def test_returns_last_line_and_first_column_of_bad_index(self, text: str) -> None:
        assert basetypes.Pos.from_str_index(text, len(text) + 5) == basetypes.Pos(len(text), 6, 0)

    def test_it_should_count_lines_by_lf_only_not_unicode_line_breaks(self) -> None:
        text = 'a: b\u2028c\nx: y'
        index = text.index('x')
        assert basetypes.Pos.from_str_index(text, index) == basetypes.Pos(index, 2, 0)

    def test_it_should_return_line_one_column_zero_for_empty_text(self) -> None:
        assert basetypes.Pos.from_str_index('', 0) == basetypes.Pos(0, 1, 0)

    def test_it_should_report_the_end_of_an_unterminated_final_line(self) -> None:
        text = 'a\nb'
        assert basetypes.Pos.from_str_index(text, len(text)) == basetypes.Pos(len(text), 2, 1)

    def test_it_should_report_the_next_line_column_zero_past_a_trailing_newline(self) -> None:
        r"""Contract 05 §Behaviour: end-of-text after a trailing `\n` is the *next* line (`syml-xreq.11`)."""
        text = 'a\nb\n'
        assert basetypes.Pos.from_str_index(text, len(text)) == basetypes.Pos(len(text), 3, 0)


def _reference_from_str_index(text: str, index: int) -> basetypes.Pos:
    r"""Original O(n)-per-call `Pos.from_str_index` body, kept only as an equivalence oracle.

    Pins the bisect-based rewrite in `basetypes.Pos.from_str_index` to the exact
    behavior (including its bad-index and unterminated-line quirks) that shipped
    before this module cached `_line_start_offsets` to fix the O(n^2) parse-time
    regression, plus the end-of-text-after-trailing-`\n` fix (Contract 05
    §Behaviour, `syml-xreq.11`): `index == len(text)` right after a trailing
    `\n` reports the *next* line, column 0, rather than staying on the last
    line that ended.
    """
    parts = text.split('\n')
    lines = [part + '\n' for part in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    if text and text.endswith('\n') and index == len(text):
        return basetypes.Pos(index, len(lines) + 1, 0)
    curr_pos = 0
    linenum = 0
    last = len(lines) - 1
    for linenum, line in enumerate(lines):
        at_unterminated_end = linenum == last and not line.endswith('\n') and curr_pos + len(line) == index
        if curr_pos + len(line) > index or at_unterminated_end:
            return basetypes.Pos(index, linenum + 1, index - curr_pos)
        curr_pos += len(line)
    return basetypes.Pos(len(text), linenum + 1, 0)


class TestPosFromStrIndexEquivalenceWithReferenceImplementation:
    """Pins `Pos.from_str_index` to `_reference_from_str_index` across boundary cases.

    Covers FR-013's positions contract: the cached bisect rewrite must be
    byte-for-byte identical to the original linear-scan algorithm, including
    empty text, a lone newline, a trailing newline, an unterminated final
    line, mid-line indices, and out-of-range indices past `len(text)`.
    """

    @pytest.mark.parametrize(
        'text',
        [
            '',
            'a',
            '\n',
            'a\n',
            'a\nb',
            'a\nb\n',
            'ab\n\ncd',
            '\n\n\n',
            'a: b\u2028c\nx: y',
        ],
    )
    def test_it_should_match_the_reference_implementation_at_every_boundary_index(self, text: str) -> None:
        candidate_indices = {0, len(text), len(text) + 5, max(len(text) // 2, 0)}
        for index in candidate_indices:
            assert basetypes.Pos.from_str_index(text, index) == _reference_from_str_index(text, index)


class TestLiteralQuoteSpanReporting:
    """Contract 08 §Original-text coordinates, for a value holding quote characters (D18).

    Quotes are ordinary characters, so the span of `key: "a"` covers the
    3-character literal text `"a"`, quotes included, in the *original* text's
    coordinates rather than the CRLF-normalized text the grammar parses.
    """

    def test_it_should_report_the_original_text_span_of_a_quote_bearing_value_on_a_crlf_line(self) -> None:
        original = 'a: b\r\nk: "a"\r\n'
        tree = parsers.parse(original, filename='doc.syml')

        source = tree.as_source()['k']

        assert source.text == '"a"'
        assert source.start == basetypes.Pos(index=9, line=2, column=3)
        assert source.end == basetypes.Pos(index=12, line=2, column=6)
        assert original[source.start.index : source.end.index] == '"a"'


class TestContinuationSpanReporting:
    """Contract 08 §Continuation spans.

    A multiline `TextLeafNode`'s `Source` keeps `start` at the value's first
    character, moves `end` to the last accepted character, and reports `text`
    as whatever `as_data()` returns for the same node — including the
    indentation preserved past the baseline (Contract 03, D11) — so
    `str(node.as_source()) == node.as_data()` holds.
    """

    def test_it_should_preserve_past_baseline_indentation_in_the_reported_span(self) -> None:
        original = 'key:\n  first\n    indented\n  back'
        tree = parsers.parse(original, filename='doc.syml')

        data = tree.as_data()
        source = tree.as_source()['key']

        assert data == {'key': 'first\n  indented\nback'}
        assert source.text == 'first\n  indented\nback'
        assert str(source) == data['key']
        assert source.start == basetypes.Pos(index=7, line=2, column=2)
        assert source.end == basetypes.Pos(index=32, line=4, column=6)


class TestUnquotedSpanReporting:
    """Contract 08 §Original-text coordinates (FR-013, R-02, US8).

    Unquoted leaf values and keys must report `Source` positions in
    *original*-text coordinates (§9.9.11-13).
    A BOM plus a CRLF line exercises both the BOM offset and the CRLF
    collapse that `PositionMap.to_original` must account for.
    """

    def test_it_should_report_the_original_text_span_of_a_key_and_unquoted_value_with_bom_and_crlf(self) -> None:
        original = '﻿key: value\r\n'
        tree = parsers.parse(original, filename='doc.syml')

        key_value = cast(KeyValue, tree.children[0].children[0])
        key_source = key_value.key.key
        value_source = tree.as_source()['key']

        assert key_source.text == 'key'
        assert key_source.start.index == 1
        assert key_source.end.index == 4
        assert original[key_source.start.index : key_source.end.index] == 'key'

        assert value_source.text == 'value'
        assert value_source.start.index == 6
        assert value_source.end.index == 11
        assert original[value_source.start.index : value_source.end.index] == 'value'


class TestFromTextCoveragePragma:
    """Contract 08 §Coverage / Contract 03 §Coverage without pragmas (FR-012).

    `Source.from_text`'s `substring is None` default branch currently
    carries `# pragma: no cover` instead of being exercised directly. A
    real call that hits the defaulting branch should cover it without any
    pragma present on the source line.
    """

    def test_it_should_cover_the_default_substring_branch_without_a_pragma(self) -> None:
        source = basetypes.Source.from_text('value')

        assert source.text == 'value'

        import inspect

        source_lines = inspect.getsource(basetypes.Source.from_text).splitlines()
        offending = [line for line in source_lines if 'substring is None' in line and 'pragma' in line]
        assert not offending, f'pragma still present on defaulting branch: {offending}'


class TestGetLineText:
    """Contract 01 pass 25: `get_line_text` replaces `syml.utils.get_line_text`."""

    def test_it_should_return_the_line_at_the_given_line_number(self) -> None:
        text = 'foo\nbar\nbaz'
        assert basetypes.get_line_text(text, 2) == 'bar'

    def test_it_should_not_treat_u2028_as_a_line_terminator(self) -> None:
        text = 'a: b c\n-   name: Alice'  # noqa: RUF001
        assert basetypes.get_line_text(text, 1) == 'a: b c'  # noqa: RUF001

    def test_it_should_return_empty_string_for_an_out_of_range_line_number(self) -> None:
        text = 'foo\nbar'
        assert basetypes.get_line_text(text, 99) == ''


class TestUtilsModuleDeleted:
    """Contract 09 §migration note 16: `syml.utils` no longer exists.

    Its sole responsibility, `get_line_text`, moved to `syml.basetypes`
    with an LF-only line lookup (Contract 01 pass 25, Contract 05).
    """

    def test_it_should_raise_module_not_found_error(self) -> None:
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module('syml.utils')


class TestLineStartOffsetsCaching:
    """Regression guard for the O(n^2) parse-time bug fixed by caching `_line_start_offsets`.

    `Source.from_node` calls `Pos.from_str_index` twice per parsed node, all
    over the same `pnode.full_text` object. Before caching, each call rescanned
    the whole document, so an n-line document did O(n) rescans of O(n) text.

    The cache used to be a process-global `functools.lru_cache`, which pinned
    up to 4 full parsed documents in memory for the life of the process (a
    MAJOR untrusted-input memory-retention finding from the syml-x0m.6.1
    remediation review). It is now scoped to a single `parsers.parse()` call
    via `basetypes.line_offset_cache_scope`, so these guards assert both the
    O(1)-amortized-per-node behavior *and* that nothing process-global remains.
    """

    def test_it_should_compute_line_start_offsets_at_most_once_per_document_while_parsing_thousands_of_nodes(
        self,
    ) -> None:
        text = ''.join(f'- item{i}\n' for i in range(8000))
        real_compute = basetypes._compute_line_start_offsets  # noqa: SLF001
        misses = 0

        def counting_compute(candidate: str) -> tuple[tuple[int, ...], bool]:
            nonlocal misses
            misses += 1
            return real_compute(candidate)

        with mock.patch.object(basetypes, '_compute_line_start_offsets', counting_compute):
            result = syml.loads(text)
        assert len(result) == 8000
        assert misses <= 2

    def test_it_should_not_expose_a_process_global_cache(self) -> None:
        assert not hasattr(basetypes._line_start_offsets, 'cache_info')  # noqa: SLF001
        assert not hasattr(basetypes._line_start_offsets, 'cache_clear')  # noqa: SLF001

    def test_it_should_release_parsed_document_memory_once_the_caller_drops_its_references(self) -> None:
        text = ''.join(f'- item{i:06d} padding-to-approximate-a-small-document\n' for i in range(2_000))
        tracemalloc.start()
        try:
            gc.collect()
            before, _peak = tracemalloc.get_traced_memory()
            result = syml.loads(text)
            assert len(result) == 2_000
            del result, text
            gc.collect()
            after, _peak = tracemalloc.get_traced_memory()
            assert after - before < 100_000
        finally:
            tracemalloc.stop()


class TestLineAboveScanScaling:
    r"""Regression guard for the O(k*n) `_line_above` bug (sp:security-review, syml-s9p9.8).

    `nodes._line_above` walks back over a run of `k` blank or column-0
    comment lines, calling `basetypes.get_line_text` once per skipped line.
    Before this fix, `get_line_text` did `text.split('\\n')` -- an O(n) scan
    of the *whole* document -- on every call, making the walk O(k*n)
    overall: a document of mostly blank lines (attacker-controlled) made
    `loads` hang. `get_line_text` now looks the line up via the cached
    `_line_start_offsets` table instead, so a full split happens at most
    once per document regardless of how many lines `_line_above` skips.
    """

    def _misses_for(self, text: str) -> int:
        real_compute = basetypes._compute_line_start_offsets  # noqa: SLF001
        misses = 0

        def counting_compute(candidate: str) -> tuple[tuple[int, ...], bool]:
            nonlocal misses
            misses += 1
            return real_compute(candidate)

        with (
            mock.patch.object(basetypes, '_compute_line_start_offsets', counting_compute),
            pytest.raises(Exception),  # noqa: B017, PT011 - any OutOfContextNodeError raise
        ):
            syml.loads(text)
        return misses

    def test_it_should_compute_line_start_offsets_at_most_once_over_a_long_blank_run(self) -> None:
        text = 'k:\n  text\n' + '\n' * 40_000 + '- x\n'

        assert self._misses_for(text) <= 1

    def test_it_should_compute_line_start_offsets_at_most_once_over_a_long_comment_run(self) -> None:
        text = 'k:\n  text\n' + '#c\n' * 40_000 + '- x\n'

        assert self._misses_for(text) <= 1

    def test_doubling_the_blank_run_should_not_roughly_quadruple_the_time(self) -> None:
        """A generous bound (< 4x for 2N) that catches quadratic blowup without pinning wall-clock exactly."""
        import time

        def timed(n: int) -> float:
            text = 'k:\n  text\n' + '\n' * n + '- x\n'
            start = time.perf_counter()
            with pytest.raises(Exception):  # noqa: B017, PT011 - any OutOfContextNodeError raise
                syml.loads(text)
            return time.perf_counter() - start

        n = 20_000
        # Warm up once (import/JIT-ish costs) so the timed runs reflect steady-state cost.
        timed(n)
        baseline = timed(n)
        doubled = timed(n * 2)

        assert doubled < baseline * 4
