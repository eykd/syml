import textwrap
from io import StringIO

import pytest
from parsimonious.nodes import Node

import syml
from syml import exceptions, nodes, parsers
from syml.basetypes import Pos, Source


class TestSymlParser:
    @pytest.fixture
    def parser(self) -> parsers.SymlParser:
        return parsers.SymlParser()

    def test_it_should_parse_a_simple_text_value(self, parser: parsers.SymlParser) -> None:
        text = textwrap.dedent('true')
        result = parser.parse(text)
        assert result.as_data() == 'true'
        assert result.as_source() == Source.from_text('true', 'true')

    def test_it_should_parse_a_simple_multiline_list(self, parser: parsers.SymlParser) -> None:
        text = textwrap.dedent(
            """
            - foo
            - bar
            - baz
            """
        )
        result = parser.parse(text)
        expected = ['foo', 'bar', 'baz']
        assert result.as_data() == expected
        assert result.as_source() == [
            Source.from_text(text, 'foo'),
            Source.from_text(text, 'bar'),
            Source.from_text(text, 'baz'),
        ]

    def test_it_should_parse_a_simple_single_line_list(self, parser: parsers.SymlParser) -> None:
        text = textwrap.dedent(
            """
            - foo
            """
        )
        result = parser.parse(text)
        assert result.as_data() == ['foo']
        assert result.as_source() == [
            Source.from_text(text, 'foo'),
        ]

    def test_it_should_parse_a_bare_list_marker_taking_its_item_from_the_next_line(
        self, parser: parsers.SymlParser
    ) -> None:
        """A bare "-" with no trailing space still opens a list item (§4.1 guard atoms).

        Per Contract 02's grammar delta, ``list_item = ("-" ws value) / ("-" &eol)``:
        a hyphen followed immediately by end-of-line is a valid, valueless list
        item whose value comes from the next (nested) line, not scalar text.
        """
        text = '-\n  block item'
        result = parser.parse(text)
        assert result.as_data() == ['block item']

    def test_it_should_parse_a_list_with_multiline_values(self, parser: parsers.SymlParser) -> None:
        text = textwrap.dedent(
            """
            - foo
            - bar
              baz
            """
        )
        result = parser.parse(text)
        expected = ['foo', 'bar\nbaz']
        assert result.as_data() == expected
        assert result.as_source() == [
            Source.from_text(text, 'foo'),
            Source.from_text(text, 'bar\n  baz', 'bar\nbaz'),
        ]

    def test_it_should_parse_a_list_with_embedded_mappings_values(self, parser: parsers.SymlParser) -> None:
        text = textwrap.dedent(
            """
            - foo:
                bar
            - baz: boo
              blah:
                baloon
            """
        )
        result = parser.parse(text)
        expected = [
            {'foo': 'bar'},
            {'baz': 'boo', 'blah': 'baloon'},
        ]
        assert result.as_data() == expected
        assert result.as_source() == [
            {Source.from_text(text, 'foo'): Source.from_text(text, 'bar')},
            {
                Source.from_text(text, 'baz'): Source.from_text(text, 'boo'),
                Source.from_text(text, 'blah'): Source.from_text(text, 'baloon'),
            },
        ]

    def test_it_should_parse_a_simple_single_line_mapping(self, parser: parsers.SymlParser) -> None:
        text = textwrap.dedent(
            """
            foo: bar
            """
        )
        result = parser.parse(text)
        assert result.as_data() == {'foo': 'bar'}
        assert result.as_source() == {Source.from_text(text, 'foo'): Source.from_text(text, 'bar')}

    def test_it_should_parse_a_simple_multiline_mapping(self, parser: parsers.SymlParser) -> None:
        text = textwrap.dedent(
            """
            foo: bar
            baz: boo
            """
        )
        result = parser.parse(text)
        expected = {'foo': 'bar', 'baz': 'boo'}
        assert result.as_data() == expected
        assert result.as_source() == {
            Source.from_text(text, 'foo'): Source.from_text(text, 'bar'),
            Source.from_text(text, 'baz'): Source.from_text(text, 'boo'),
        }

    def test_it_should_drop_a_zero_length_inline_value_after_a_key_colon(self, parser: parsers.SymlParser) -> None:
        """D6, §9.3: ``key:␠`` lexes with an empty inline ``text`` child.

        A zero-length inline value is normalized to "no inline
        value at all", identical to ``key:`` with nothing after it -- the
        node stays open and accepts the following nested block instead of
        treating the empty text as the value.
        """
        text = 'key: \n  nested: content'
        result = parser.parse(text)
        assert result.as_data() == {'key': {'nested': 'content'}}

    def test_it_should_drop_a_zero_length_inline_value_after_a_list_item_dash(self) -> None:
        """D6, §9.3: ``-␠`` lexes with an empty inline ``text`` child.

        A zero-length inline value is normalized to "no inline
        value at all", identical to ``-`` with nothing after it -- the list
        item node stays open and accepts the following nested block instead
        of treating the empty text as the value.
        """
        text = '- \n  x'
        result = syml.loads(text)
        assert result == ['x']

    def test_it_should_lex_ambiguous_colon_and_dash_forms_as_data_scalars(self, parser: parsers.SymlParser) -> None:
        """§7.6 lexing-outcomes table: colon/dash forms that fall through to ``data``.

        ``key:value`` and ``key:v`` (no space after the colon) do not lex as
        ``key_value`` -- the colon-adjacent value requires a leading space or
        tab per §4.1, so these fall through to a bare ``data`` scalar
        (US3 scenario 3 and scenario 5's sibling). ``-item`` and ``-42`` are
        not list markers -- ``list_item`` requires ``-`` to be followed by
        whitespace or end-of-line, so a bare dash-prefixed word or number
        also falls through to a bare ``data`` scalar (US3 scenario 4).
        """
        assert parser.parse('key:value').as_data() == 'key:value'
        assert parser.parse('key:v').as_data() == 'key:v'
        assert parser.parse('-item').as_data() == '-item'
        assert parser.parse('-42').as_data() == '-42'

    def test_it_should_treat_a_tab_after_the_colon_as_separator_whitespace(self) -> None:
        r"""§4.1 grammar ``ws = ~"[ \t]+"``: a tab satisfies the required separator too (xreq.19).

        A tab immediately after the colon now satisfies ``ws`` exactly like a
        space, so ``key:\tv`` lexes as a key/value mapping, not a bare
        ``data`` scalar (superseded D5).
        """
        assert syml.loads('key:\tv') == {'key': 'v'}

    def test_it_should_not_parse_a_key_containing_a_control_character_as_a_mapping(
        self, parser: parsers.SymlParser
    ) -> None:
        r"""D15: the key class is ``\s`` plus an enumerated control-character exclusion.

        Per §4.5, ``\s`` in the key grammar denotes exactly the Unicode
        ``White_Space`` set. ``\x01`` is not part of that set, so it is not
        matched by Python's ``\s`` either -- it is excluded only by the
        additional enumerated ranges (``\x00-\x1f\x7f-\x9f``) that the key
        class carries alongside ``\s``. So ``a\x01b: v`` must NOT lex as a
        key/value pair; it falls through to a bare data value instead.
        """
        text = 'a\x01b: v'
        result = parser.parse(text)
        assert result.as_data() != {'a\x01b': 'v'}

    def test_it_should_parse_a_weirdly_nested_mapping(self, parser: parsers.SymlParser) -> None:
        text = textwrap.dedent(
            """
            foo: bar: blah
            baz: boo
            """
        )
        result = parser.parse(text)
        expected = {'foo': 'bar: blah', 'baz': 'boo'}
        assert result.as_data() == expected
        assert result.as_source() == {
            Source.from_text(text, 'foo'): Source.from_text(text, 'bar: blah'),
            Source.from_text(text, 'baz'): Source.from_text(text, 'boo'),
        }

    def test_it_should_parse_a_nested_mapping_with_list(self, parser: parsers.SymlParser) -> None:
        text = textwrap.dedent(
            """
            foo:
              - bar
              - baz
            blah: boo
            """
        )
        result = parser.parse(text)
        expected = {'blah': 'boo', 'foo': ['bar', 'baz']}
        assert result.as_data() == expected
        assert result.as_source() == {
            Source.from_text(text, 'foo'): [Source.from_text(text, 'bar'), Source.from_text(text, 'baz')],
            Source.from_text(text, 'blah'): Source.from_text(text, 'boo'),
        }

    def test_it_should_parse_a_nested_mapping_with_weirdly_nested_list(self, parser: parsers.SymlParser) -> None:
        text = textwrap.dedent(
            """
            foo: - bar
            blah: boo
            """
        )
        result = parser.parse(text)
        expected = {'foo': '- bar', 'blah': 'boo'}
        assert result.as_data() == expected
        assert result.as_source() == {
            Source.from_text(text, 'foo'): Source.from_text(text, '- bar'),
            Source.from_text(text, 'blah'): Source.from_text(text, 'boo'),
        }

    def test_it_should_parse_a_nested_list_with_mapping(self, parser: parsers.SymlParser) -> None:
        text = textwrap.dedent(
            """
            - foo:
              - bar
              - baz
            - blah: boo
            """
        )
        result = parser.parse(text)
        expected = [
            {'foo': ['bar', 'baz']},
            {'blah': 'boo'},
        ]
        assert result.as_data() == expected
        assert result.as_source() == [
            {
                Source.from_text(text, 'foo'): [Source.from_text(text, 'bar'), Source.from_text(text, 'baz')],
            },
            {
                Source.from_text(text, 'blah'): Source.from_text(text, 'boo'),
            },
        ]

    def test_it_should_parse_comments_and_blanks(self, parser: parsers.SymlParser) -> None:
        """A column-0 comment is dropped; blank lines are dropped (principal ruling 2026-09-24, xreq.21).

        An indented comment (e.g. between ``- bar`` and ``- baz`` at column
        2) is no longer a comment at all -- ``comment`` only matches at
        column 0 -- so it now lexes as text and needs Contract 02's text
        context to join a structure-shaped continuation; that scenario is
        pinned in the text-context leaf, not here (Contract 01 §Behaviour).
        """
        text = textwrap.dedent(
            """
            # A comment
            - foo:

              - bar
              - baz

            - blah: boo # not a comment!

            """
        )
        result = parser.parse(text)
        expected = [{'foo': ['bar', 'baz']}, {'blah': 'boo # not a comment!'}]
        assert result.as_data() == expected
        assert result.as_source() == [
            {
                Source.from_text(text, 'foo'): [Source.from_text(text, 'bar'), Source.from_text(text, 'baz')],
            },
            {
                Source.from_text(text, 'blah'): Source.from_text(text, 'boo # not a comment!'),
            },
        ]

    def test_it_fails_parsing_weird_indentations(self, parser: parsers.SymlParser) -> None:
        bad_yaml = textwrap.dedent(
            """
              - foo:
                  - bar
             - baz
            - blah
            """
        )
        with pytest.raises(exceptions.OutOfContextNodeError):
            parser.parse(bad_yaml)

    def test_it_should_compute_level_from_a_nodes_own_column_not_the_lines_indent(
        self, parser: parsers.SymlParser
    ) -> None:
        """A list-item line's inline mapping key is leveled by its own column (R-11).

        ``-   name: Alice`` puts ``name`` at column 4. A continuation line
        indented only to column 2 is therefore *less* indented than ``name``'s
        own level, so it cannot incorporate as a sibling under the same
        mapping and the parse must fail with ``OutOfContextNodeError`` — not
        succeed by inheriting the list item's column 0 for ``name``.
        """
        text = '-   name: Alice\n  role: admin'
        with pytest.raises(exceptions.OutOfContextNodeError):
            parser.parse(text)


class TestSimpleParserFunction:
    def test_it_should_parse_a_simple_list(self) -> None:
        text = textwrap.dedent(
            """
            - foo
            - true
            - false
            """
        )
        result = parsers.parse(text).as_data()
        assert result == [
            'foo',
            'true',
            'false',
        ]

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            ('key:\n  first\n    indented\n  back', {'key': 'first\n  indented\nback'}),
            ('hello\n  world\nagain', 'hello\n  world\nagain'),
        ],
    )
    def test_it_should_preserve_indentation_deeper_than_the_continuation_baseline(
        self, text: str, expected: object
    ) -> None:
        """A continuation line indented deeper than the value's baseline keeps its extra spaces (§5.3, D11, todo.txt A9)."""
        assert syml.loads(text) == expected

    def test_it_should_join_a_continuation_line_under_an_inline_key_value(self) -> None:
        """An inline key/value value must set inline=True so its baseline stays open (D11).

        'Big Warning: do not touch' fails the key_value grammar (space before
        the colon) and falls through to plain text, so it should join as a
        continuation of 'Note' rather than raising OutOfContextNodeError.
        """
        text = 'a: Note\n  Big Warning: do not touch'
        assert syml.loads(text) == {'a': 'Note\nBig Warning: do not touch'}

    def test_it_should_report_out_of_context_position_in_original_text_coordinates_on_bom_crlf_documents(
        self,
    ) -> None:
        """Contract 05: `OutOfContextNodeError.position` must anchor to original-text coordinates.

        `SymlNode.fail_to_incorporate_node` builds its `Pos` from
        `pnode.full_text` (the NORMALIZED text) and never threads it through
        `PositionMap.to_original`, unlike leaf `Source`s (Contract 08). On a
        BOM- and CRLF-prefixed document the CRLF collapses shift every
        normalized-text index leftward relative to the original document, so
        the reported position diverges from where the offending line
        actually sits in the caller's original text.
        """
        text = '﻿  - foo:\r\n      - bar\r\n - baz\r\n- blah\r\n'
        expected_position = Pos.from_str_index(text, text.index('- baz'))
        with pytest.raises(exceptions.OutOfContextNodeError) as exc_info:
            syml.loads(text)
        assert exc_info.value.position == expected_position

    def test_it_should_report_container_node_source_in_original_text_coordinates_on_bom_crlf_documents(
        self,
    ) -> None:
        """Contract 08: a container node's own `Source` must also anchor to original-text coordinates.

        `SymlNode.__post_init__` builds every node's `source` from its raw
        `pnode` via `Source.from_node`, which uses normalized-text
        coordinates. Leaf nodes (`TextLeafNode`, `KeyLeafNode`) get
        re-anchored afterward through `PositionMap.to_original_source`, but a
        container node (e.g. `KeyValue`, `Mapping`, `ListItem`) never is, so
        its `source.start` stays in normalized-text coordinates even though
        leaf `Source`s alongside it are in original-text coordinates.
        """
        text = '﻿key:\r\n  value\r\n'
        expected_start = Pos.from_str_index(text, text.index('key:'))
        root = parsers.parse(text)
        mapping = root.children[0]
        key_value = mapping.children[0]
        assert key_value.source.start == expected_start

    def test_it_should_report_line_number_and_line_text_using_lf_only_splitting(self) -> None:
        r"""`ParseError.line_text` and `.position.line` must use LF-only line splitting (§13.3).

        A U+2028 LINE SEPARATOR inside a value on line 1 must not start a new
        line: it is not a line terminator under SYML's LF-only rule. The
        second (and only other) LF-delimited line is ``-   name: Alice``,
        which then collides with the top-level key/value on line 1 and
        raises `OutOfContextNodeError` anchored at line 2.

        `utils.get_line_text` (via `utils.split_lines`) currently calls
        `str.splitlines()`, which *does* treat U+2028 as a line terminator
        (Contract 01 pass 25, Contract 08 gap 16). That silently
        renumbers every line after the U+2028 by one, so `line_text` reports
        the wrong line's contents even though `position.line` (computed by
        `Pos.from_str_index`, which already splits on ``\\n`` only) is correct.
        """
        text = 'a: b c\n-   name: Alice\n  role: admin'  # noqa: RUF001
        with pytest.raises(exceptions.OutOfContextNodeError) as exc_info:
            parsers.parse(text)
        assert exc_info.value.position.line == 2
        assert exc_info.value.line_text == '-   name: Alice'

    def test_it_should_run_preprocessing_and_raise_tab_indentation_error(self) -> None:
        """`parsers.parse` must run §9.0's `preprocess` before lexing (Contract 02, R-09).

        Contract 02's entry-point pseudocode opens with
        ``doc = preprocess(text, filename)`` ahead of the per-line lexing
        loop, so every document passes through the tab-indentation scan
        (§9.0.3, D14) on the way in. Today `parsers.parse` hands the raw
        text straight to the whole-document grammar and never calls
        `preprocess`, so a tab in a line's leading whitespace is silently
        accepted instead of raising `TabIndentationError`.
        """
        text = 'a:\n\tx: 1\n'
        with pytest.raises(exceptions.TabIndentationError):
            parsers.parse(text)

    def test_it_should_parse_whats_in_the_readme_text_only(self) -> None:
        text = textwrap.dedent(
            """
            foo:
              - bar
              - baz
              - blah
                boo
                baloon

            booleans:
              - True
              - False
              - true
              - false
              - TRUE
              - FALSE
            """
        )
        result = syml.loads(text)
        assert result == {
            'foo': [
                'bar',
                'baz',
                'blah\nboo\nbaloon',
            ],
            'booleans': [
                'True',
                'False',
                'true',
                'false',
                'TRUE',
                'FALSE',
            ],
        }

    def test_it_should_parse_whats_in_the_readme_text_only_from_a_fileobj(self) -> None:
        buf = StringIO(
            textwrap.dedent(
                """
            foo:
              - bar
              - baz
              - blah
                boo
                baloon

            booleans:
              - True
              - False
              - true
              - false
              - TRUE
              - FALSE
            """
            )
        )
        result = syml.load(buf)
        assert result == {
            'foo': [
                'bar',
                'baz',
                'blah\nboo\nbaloon',
            ],
            'booleans': [
                'True',
                'False',
                'true',
                'false',
                'TRUE',
                'FALSE',
            ],
        }


class TestVisitCommentWithNoTrailingText:
    """FR-009: no third-party exception may escape `loads` (Contract 05).

    A comment-only line whose markers consume the whole line (e.g. `'####'`)
    leaves the grammar's optional trailing `text?` unmatched. Parsimonious
    visits that unmatched optional to `None`, not a zero-length node, so
    `visit_comment`'s `text.pnode` access raises `AttributeError`, which
    Parsimonious re-wraps as `parsimonious.exceptions.VisitationError` --
    a third-party exception type that must never escape `syml.loads`.
    """

    def test_a_comment_only_document_does_not_leak_a_parsimonious_exception(self) -> None:
        """Parsing `'####'` must not raise `parsimonious.exceptions.VisitationError`."""
        try:
            result = syml.loads('####')
        except exceptions.ParseError:
            pass
        else:
            assert isinstance(result, str)


class TestUnwrappedRecursionError:
    """Contract 05 §Other Parsimonious exceptions, rule 1.

    `unwrapped_exceptions = (ParseError, RecursionError)` so a recursion
    overflow raised from inside a `visit_*` method surfaces as the host
    `RecursionError`, never `parsimonious.exceptions.VisitationError`. A
    deeply nested inline structure overflows the interpreter's own recursion
    limit inside `Grammar.parse` before `NodeVisitor.visit` ever runs, so it
    can't discriminate what `unwrapped_exceptions` governs; this class also
    forces the overflow to happen *inside* a `visit_*` method directly.
    """

    def test_a_single_deep_inline_list_line_raises_the_host_recursion_error(self) -> None:
        """`'- ' * 200 + 'x'` must raise `RecursionError`, never `VisitationError`."""
        with pytest.raises(RecursionError):
            syml.loads('- ' * 200 + 'x')

    def test_a_recursion_error_raised_inside_a_visit_method_crosses_the_visitor_unwrapped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A `RecursionError` raised from a `visit_*` method must not become `VisitationError`."""

        def fake_visit_text(_self: parsers.SymlParser, _node: Node, _children: object) -> None:
            raise RecursionError

        monkeypatch.setattr(parsers.SymlParser, 'visit_text', fake_visit_text)

        with pytest.raises(RecursionError):
            parsers.SymlParser().parse('key: value')


class TestKeyPatternFallsThroughToText:
    """`key = ~"[a-z][a-z0-9_-]*"` (§4.5, xreq.16): ASCII, lowercase, leading letter, or it is not a key.

    A line whose would-be key fails that pattern -- not just an uppercase
    code point, but any non-ASCII, non-leading-letter, or otherwise
    unmatched key -- simply fails the `key_value`/`section` alternative of
    `structure`, so `value = structure / data` falls through to `data`
    (plain text) for the whole line, exactly as if no structure rule had
    been tried at all. There is no D19-style special case in the visitor
    any more: the grammar alone decides.
    """

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            ('1: x', '1: x'),
            ('_x: x', '_x: x'),
            ('-x: x', '-x: x'),
            ('e.mail: x', 'e.mail: x'),
            ('\u540d\u524d: x', '\u540d\u524d: x'),
            ('\u00df: x', '\u00df: x'),
            ('URL: x', 'URL: x'),
            ('firstName: x', 'firstName: x'),
            ('\u00c9t\u00e9: chaud', '\u00c9t\u00e9: chaud'),
            ('a:\n  B: c', {'a': 'B: c'}),
            ('x:\n  - Listen: here', {'x': ['Listen: here']}),
            ('- Listen: here', ['Listen: here']),
            ('a: Note\n  Listen: here', {'a': 'Note\nListen: here'}),
        ],
    )
    def test_a_key_value_line_with_an_unmatched_key_is_text(self, text: str, expected: object) -> None:
        assert syml.loads(text) == expected

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            ('\u00c9t\u00e9:', '\u00c9t\u00e9:'),
            ('a:\n  B:', {'a': 'B:'}),
            ('- Listen:', ['Listen:']),
        ],
    )
    def test_a_section_line_with_an_unmatched_key_is_text(self, text: str, expected: object) -> None:
        assert syml.loads(text) == expected

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            ('choice1: x', {'choice1': 'x'}),
            ('first-name: x', {'first-name': 'x'}),
            ('first_name: x', {'first_name': 'x'}),
            ('effect: x', {'effect': 'x'}),
            ('look-in-dark:', {'look-in-dark': ''}),
        ],
    )
    def test_a_key_matching_the_pattern_still_lexes_as_structure(self, text: str, expected: object) -> None:
        assert syml.loads(text) == expected

    def test_the_fallthrough_leaf_spans_the_whole_line_at_the_root(self) -> None:
        root = parsers.parse('\u00c9t\u00e9: chaud')

        leaf = root.children[0]

        assert isinstance(leaf, nodes.TextLeafNode)
        assert leaf.source.text == '\u00c9t\u00e9: chaud'
        assert leaf.source.start == Pos(index=0, line=1, column=0)
        assert leaf.source.end == Pos(index=10, line=1, column=10)

    def test_the_fallthrough_leaf_spans_the_whole_line_under_a_key(self) -> None:
        root = parsers.parse('a:\n  B: c')

        leaf = root.children[0].children[0].children[0]

        assert isinstance(leaf, nodes.TextLeafNode)
        assert leaf.source.text == 'B: c'
        assert leaf.source.start == Pos(index=5, line=2, column=2)
        assert leaf.source.end == Pos(index=9, line=2, column=6)

    def test_the_fallthrough_leaf_spans_the_rest_of_the_line_after_a_list_marker(self) -> None:
        root = parsers.parse('- Listen:')

        leaf = root.children[0].children[0].children[0]

        assert isinstance(leaf, nodes.TextLeafNode)
        assert leaf.inline is True
        assert leaf.source.text == 'Listen:'
        assert leaf.source.start == Pos(index=2, line=1, column=2)
        assert leaf.source.end == Pos(index=9, line=1, column=9)

    def test_the_fallthrough_leaf_reports_original_text_coordinates_on_a_bom_crlf_document(self) -> None:
        original = '\ufeffx:\r\n  B: c\r\n'

        source = parsers.parse(original).as_source()['x']

        assert source.text == 'B: c'
        assert original[source.start.index : source.end.index] == 'B: c'


class TestQuotesAreLiteralText:
    """D18: SYML has no quoted strings; `'` and `"` are ordinary characters."""

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            ('k: \'Tis\n  "q"', {'k': '\'Tis\n"q"'}),
            ('- "x" y', ['"x" y']),
            ('k: ""', {'k': '""'}),
            ("k: ''", {'k': "''"}),
            ('key: "a" trailing', {'key': '"a" trailing'}),
            ("- 'x'", ["'x'"]),
            ('"just text"', '"just text"'),
        ],
    )
    def test_it_should_keep_quote_characters_as_part_of_the_value(self, text: str, expected: object) -> None:
        assert syml.loads(text) == expected

    def test_a_quote_bearing_inline_value_still_accepts_continuation_lines(self) -> None:
        """An inline value that begins with a quote is ordinary text, so it is never 'complete'."""
        assert syml.loads('k: "a"\n  b') == {'k': '"a"\nb'}


class TestGrammarIdentity:
    """Contract 01 test obligation 1: code and SYML-SPECIFICATION.md §4.1 carry the same grammar.

    Loads §4.1's fenced ``peg`` block with `parsimonious.Grammar` and
    compares every rule's `as_rule()` text against `SymlParser.grammar`,
    plus both grammars' `default_rule.name`. Runs under the repository's
    `error::SyntaxWarning` policy (pyproject `filterwarnings`), so a
    non-raw escape in either grammar fails this test at construction time.
    """

    def test_the_spec_and_code_grammars_are_identical(self) -> None:
        import re
        from pathlib import Path

        from parsimonious import Grammar

        spec_path = Path(__file__).parent.parent / 'SYML-SPECIFICATION.md'
        spec_text = spec_path.read_text(encoding='utf-8')
        match = re.search(r'```peg\n(.*?)```', spec_text, re.DOTALL)
        assert match is not None, 'SYML-SPECIFICATION.md must have a fenced ```peg block in §4.1'
        spec_grammar = Grammar(match.group(1))

        code_rules = {name: rule.as_rule() for name, rule in parsers.SymlParser.grammar.items()}
        spec_rules = {name: rule.as_rule() for name, rule in spec_grammar.items()}
        assert spec_rules == code_rules
        assert spec_grammar.default_rule.name == 'document'
        assert parsers.SymlParser.grammar.default_rule.name == 'document'


class TestContract01BehaviourTable:
    r"""Contract 01 §Behaviour: one parametrized test per table row (test obligation 2).

    Excludes the one row marked "Not a grammar-leaf test" (the 8-space
    ``-\\tk: v\\n        j: w`` continuation, which needs Contract 02's text
    context and is pinned there instead).
    """

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            # Keys (FR-001).
            ('choice1: x', {'choice1': 'x'}),
            ('first-name: x', {'first-name': 'x'}),
            ('first_name: x', {'first_name': 'x'}),
            ('1: x', '1: x'),
            ('_x: x', '_x: x'),
            ('-x: x', '-x: x'),
            ('e.mail: x', 'e.mail: x'),
            ('\u540d\u524d: x', '\u540d\u524d: x'),
            ('\u00df: x', '\u00df: x'),
            ('URL: x', 'URL: x'),
            ('firstName: x', 'firstName: x'),
            ('- [ask: why?]', ['[ask: why?]']),
            ('- 3: 1 odds', ['3: 1 odds']),
            ('"so: you came back."', '"so: you came back."'),
            # Separator whitespace (FR-008).
            ('k:\tv', {'k': 'v'}),
            ('k: \tv', {'k': 'v'}),
            ('a:\t\n  b: 1', {'a': {'b': '1'}}),
            ('- a\n-\tx', ['a', 'x']),
            ('k: a\tb', {'k': 'a\tb'}),
            ('-\tk: v\n  j: w', [{'k': 'v', 'j': 'w'}]),
            # Indentation (FR-009).
            ('\xa0k: v', '\xa0k: v'),
            ('\x0bx', '\x0bx'),
            ('\x0c', '\x0c'),
            ('\u2028- x', '\u2028- x'),
            ('\xa0', '\xa0'),
            ('a: 1\n  \t  \nb: 2', {'a': '1', 'b': '2'}),
            # Comments (FR-007, principal ruling 2026-09-24).
            ('# c', ''),
            ('#', ''),
            ('//', ''),
            ('# c\n', ''),
            ('# Application config\nname: app\nport: 80', {'name': 'app', 'port': '80'}),
            ('// header\nname: app', {'name': 'app'}),
            ('a: 1\n# note\nb: 2', {'a': '1', 'b': '2'}),
            ('- a\n# note\n- b', ['a', 'b']),
            ('a:\n# section\n  b: 1', {'a': {'b': '1'}}),
            ('hello\n# note\nworld', 'hello\nworld'),
            ('#tag: value', ''),
            ('///x\nk: v', {'k': 'v'}),
            ('#!/bin/sh\nk: v', {'k': 'v'}),
            ('#\tx\nk: v', {'k': 'v'}),
            ('//\tx\nk: v', {'k': 'v'}),
            ('\ufeff# header\nk: v', {'k': 'v'}),
            ('\xa0# x', '\xa0# x'),
            ('/x', '/x'),
            ('port: 8080 # default', {'port': '8080 # default'}),
            # Document shape.
            ('k: v', {'k': 'v'}),
            ('k: v\n', {'k': 'v'}),
            ('', ''),
            ('\n', ''),
            ('\n  \n\t\n', ''),
        ],
    )
    def test_a_behaviour_table_row_produces_its_stated_output(self, text: str, expected: object) -> None:
        assert syml.loads(text) == expected

    def test_a_tab_in_leading_whitespace_raises_tab_indentation_error(self) -> None:
        with pytest.raises(exceptions.TabIndentationError):
            syml.loads('a:\n\tb')

    def test_a_comment_does_not_hide_a_following_tab_indented_line(self) -> None:
        with pytest.raises(exceptions.TabIndentationError) as exc_info:
            syml.loads('# c\n\tb')
        assert exc_info.value.position == Pos(index=4, line=2, column=0)

    def test_a_bom_after_index_0_is_content_not_a_comment(self) -> None:
        with pytest.raises(exceptions.OutOfContextNodeError):
            syml.loads('a: 1\n\ufeff# x')

    def test_a_comment_does_not_hide_a_following_structure_shaped_line(self) -> None:
        with pytest.raises(exceptions.OutOfContextNodeError) as exc_info:
            syml.loads('a: 1\n# c\n- x')
        assert exc_info.value.position == Pos(index=9, line=3, column=0)


class TestContract02TextContextBehaviourTable:
    r"""Contract 02 §Behaviour / §Test obligations 1: one parametrized test per pinned row.

    Structure is lexed only at a block's first line; once a value is text,
    every later line at or past its baseline is that value's text too,
    whatever shape it lexes to. Covers the US1/US2 scenario rows, the R-06
    rows, the `edge` rows, and all eight `silent` rows the leaf ordering
    (plan.md §Leaf Ordering item 3, Contract 02 lines 154-169) assigns to
    this leaf — including the ``-\\tk: v\\n        j: w`` row Contract 01
    excludes as "Not a grammar-leaf test".
    """

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            # US1-3: a dash-shaped continuation is text.
            ('k:\n  some prose\n  - used as a dash\n  more', {'k': 'some prose\n- used as a dash\nmore'}),
            # US1-4: an indented //, # continuation is text.
            ('- Share is\n  //server/share', ['Share is\n//server/share']),
            ('- tag line\n  #winning', ['tag line\n#winning']),
            # US1-7: uppercase KEY: lines are text.
            ('env:\n  HOME: /h\n  PATH: /p', {'env': 'HOME: /h\nPATH: /p'}),
            # US1-9: a text root scalar stays text throughout.
            ('Given:\n  a: 1', 'Given:\n  a: 1'),
            # US1-16: inline value plus deeper lines of any shape.
            ('k: first\n  - second\n  key: third', {'k': 'first\n- second\nkey: third'}),
            # US1-17 (negative control): the first line still decides structure.
            ('k:\n  - a\n  - b', {'k': ['a', 'b']}),
            ('k:\n  x: 1\n  y: 2', {'k': {'x': '1', 'y': '2'}}),
            # US1-24: a trailing "comment" after key: is the inline text value.
            ('server: # prod\n  host: x', {'server': '# prod\nhost: x'}),
            # R-06: a later key-shaped or dash-shaped line joins the open value.
            ('k:\n  a: 1\n   b: 2', {'k': {'a': '1\nb: 2'}}),
            ('- eggs\n - bread', ['eggs\n- bread']),
            ('a: 1\n  - x', {'a': '1\n- x'}),
            ('parent:\n  child1: a\n   child2: b', {'parent': {'child1': 'a\nchild2: b'}}),
            # edge: a text root scalar's first line, dash included.
            ('hello\nk: v', 'hello\nk: v'),
            ('---\nk: v', '---\nk: v'),
            # silent (Contract 02 'silent' rows): an indented first-line `#`
            # makes the whole block text.
            ('a:\n  # section\n  b: 1\n  c: 2', {'a': '# section\nb: 1\nc: 2'}),
            # silent, "Not a grammar-leaf test" (Contract 01): the tab is one column.
            ('-\tk: v\n        j: w', [{'k': 'v\nj: w'}]),
            # silent: a NBSP after key: is not separator whitespace, so the
            # first line is text and the root is text throughout.
            ('name:\xa0app\nport: 80', 'name:\xa0app\nport: 80'),
            # silent: a `#` after key: is the inline text value; the block
            # under it joins it.
            ('server: # production\n  host: x\n  port: 80', {'server': '# production\nhost: x\nport: 80'}),
            ('- # item note\n  name: x', ['# item note\nname: x']),
            # silent: a trailing invisible character after `key: `/`- ` is a
            # non-empty inline text value (FR-009); the block under it joins it.
            ('x: 1\nserver: \xa0\n  host: a\n  port: 80', {'x': '1', 'server': '\xa0\nhost: a\nport: 80'}),
            ('- \xa0\n  name: x', ['\xa0\nname: x']),
            # silent: a line of only a NBSP, FF, or other non-space character
            # is content, not blank; as a block's first line it makes the
            # block text.
            ('k: v\n \xa0\nj: w', {'k': 'v\n\xa0', 'j': 'w'}),
            ('k:\n  a\n  \xa0\n  b', {'k': 'a\n\xa0\nb'}),
            ('k:\n  \x0c\n  b: 1', {'k': '\x0c\nb: 1'}),
            # silent: a non-pattern first key makes the item's inline value
            # text, anchored at the `-` column.
            (
                'ports:\n  - containerPort: 80\n    protocol: TCP',
                {'ports': ['containerPort: 80\nprotocol: TCP']},
            ),
        ],
    )
    def test_a_behaviour_table_row_produces_its_stated_output(self, text: str, expected: object) -> None:
        assert syml.loads(text) == expected

    @pytest.mark.parametrize(
        'text',
        [
            # US1-18: a line below the fixed baseline ends the value and
            # still finds no context, unchanged.
            'k: a\n    b\n  c',
            # edge: a shallower plain-text line after a text root scalar's
            # first line is still out of context.
            'k: v\nhello',
            # edge: a non-pattern LATER key sits at the open mapping's
            # column and still raises (the contrast with the silent 'ports'
            # row, whose non-pattern key is the item's FIRST line).
            '- name: x\n  Age: 3',
        ],
    )
    def test_a_behaviour_table_row_raises_out_of_context(self, text: str) -> None:
        with pytest.raises(exceptions.OutOfContextNodeError):
            syml.loads(text)


class TestContract02ParagraphBreakBehaviourTable:
    r"""Contract 02 §Behaviour / §Test obligations 1: the paragraph-break (rule 4) rows.

    One physical blank line between two lines of the same value survives as
    one empty line in `as_data()`, counted from the NORMALIZED text's line
    breaks at attach time (R-03). A column-0 comment line in the gap is
    neither a line of the value nor a blank line: it is skipped when
    counting, and every physical blank line on either side of it still
    counts (principal's blank-lines ruling, 2026-09-24).
    """

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            # US1-1: a block value's paragraph break survives.
            ('k:\n  Para one.\n\n  Para two.', {'k': 'Para one.\n\nPara two.'}),
            # US1-2: a root scalar's paragraph break survives.
            ('Para one.\n\nPara two.', 'Para one.\n\nPara two.'),
            # US1-11: multiple consecutive blanks count individually;
            # trailing blanks after the value's last line are inert.
            ('k:\n  a\n\n\n  b\n\n', {'k': 'a\n\n\nb'}),
            # US1-12: a blank before the first continuation is inert.
            ('k:\n\n  a', {'k': 'a'}),
            # US1-13: a blank before the next key is inert.
            ('k:\n  a\n\nb: 2', {'k': 'a', 'b': '2'}),
            # US1-21: a column-0 comment between two lines is skipped, not
            # counted as a blank (0 blank lines).
            ('k:\n  a\n# note\n  b', {'k': 'a\nb'}),
            # US1-22 / principal's ruling (2026-09-24): a column-0 comment
            # flanked by real blanks doesn't swallow them — both sides
            # still count (the literal as-if-not-there reading).
            ('k:\n  a\n\n# note\n\n  b', {'k': 'a\n\n\nb'}),
            ('k:\n  a\n\n# note\n  b', {'k': 'a\n\nb'}),
            # R-03: a whitespace-only line is blank too.
            ('k:\n  a\n      \n  b', {'k': 'a\n\nb'}),
            # R-04: an inline value's first line counts too.
            ('k: first\n\n  second', {'k': 'first\n\nsecond'}),
        ],
    )
    def test_a_behaviour_table_row_produces_its_stated_output(self, text: str, expected: object) -> None:
        assert syml.loads(text) == expected

    def test_as_source_round_trips_through_str_with_paragraph_breaks(self) -> None:
        """`str(node.as_source()) == node.as_data()` still holds with paragraph breaks (Contract 02)."""
        result = parsers.parse('k:\n  Para one.\n\n  Para two.')
        assert str(result.as_source()['k']) == result.as_data()['k']


class TestVisitLineReturnsNone:
    r"""Contract 01 test obligation 3: `visit_line` returns `None` for a blank content span or a comment.

    Not for `"\\xa0"` (a NBSP-only line is text, not blank) or an indented
    `# x` (an indented `#`/`//` line is not a comment, only text).
    """

    @pytest.mark.parametrize('text', ['', '   ', '\t', ' \t ', '# a comment'])
    def test_it_returns_none(self, text: str) -> None:
        line_node = parsers.SymlParser.grammar['line'].parse(text)
        assert parsers.SymlParser().visit(line_node) is None

    @pytest.mark.parametrize('text', ['\xa0', '  # x'])
    def test_it_does_not_return_none(self, text: str) -> None:
        line_node = parsers.SymlParser.grammar['line'].parse(text)
        assert parsers.SymlParser().visit(line_node) is not None
