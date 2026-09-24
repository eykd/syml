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

    def test_it_should_not_treat_a_tab_after_the_colon_as_separator_whitespace(self) -> None:
        r"""§4.1 grammar ``ws = ~" +"``: only a space satisfies the required separator.

        A tab immediately after the colon never satisfies ``ws``, and there is
        no key_value guard without a space, so the whole line falls through to
        a bare ``data`` scalar unchanged. Currently ``src/syml/parsers.py``
        defines ``ws = ~"[ \\t]+"`` (tab accepted), which contradicts the spec
        and incorrectly lexes this as a key/value mapping.
        """
        assert syml.loads('key:\tv') == 'key:\tv'

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
        text = textwrap.dedent(
            """
            # A comment
            - foo:

              - bar
              # Something else entirely
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

            booleans?:
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
            'booleans?': [
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

            booleans?:
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
            'booleans?': [
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


class TestKeyHasUppercase:
    """D19, §4.5: a key may not contain a code point of General_Category Lu or Lt."""

    @pytest.mark.parametrize(
        'key',
        [
            'effect',
            'look-in-dark',
            '名前',
            '\u216b',  # ROMAN NUMERAL TWELVE is Nl, not uppercase
            '\u217b',  # SMALL ROMAN NUMERAL TWELVE is Nl too
            'k1_2',
            '',
        ],
    )
    def test_it_should_accept_a_key_with_no_uppercase_code_point(self, key: str) -> None:
        assert parsers.key_has_uppercase(key) is False

    @pytest.mark.parametrize(
        'key',
        [
            'Name',
            'nAme',
            '\u00c9t\u00e9',  # É is Lu
            '\u01c5',  # ǅ LATIN CAPITAL LETTER D WITH SMALL LETTER Z WITH CARON is Lt
            '\u0394elta',  # Greek capital delta is Lu
        ],
    )
    def test_it_should_reject_a_key_with_an_uppercase_or_titlecase_code_point(self, key: str) -> None:
        assert parsers.key_has_uppercase(key) is True


class TestUppercaseKeyFallsThroughToText:
    """D19: a line whose would-be key contains an uppercase code point is a text line.

    `visit_key_value` and `visit_section_line` both hand back a
    `TextLeafNode` over the whole line, exactly as if it had lexed as `data`,
    whether the line sits at the root, under a key, or inline after a list
    marker.
    """

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            ('\u00c9t\u00e9: chaud', '\u00c9t\u00e9: chaud'),
            ('a:\n  B: c', {'a': 'B: c'}),
            ('x:\n  - Listen: here', {'x': ['Listen: here']}),
            ('- Listen: here', ['Listen: here']),
            ('a: Note\n  Listen: here', {'a': 'Note\nListen: here'}),
        ],
    )
    def test_a_key_value_line_with_an_uppercase_key_is_text(self, text: str, expected: object) -> None:
        assert syml.loads(text) == expected

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            ('\u00c9t\u00e9:', '\u00c9t\u00e9:'),
            ('a:\n  B:', {'a': 'B:'}),
            ('- Listen:', ['Listen:']),
        ],
    )
    def test_a_section_line_with_an_uppercase_key_is_text(self, text: str, expected: object) -> None:
        assert syml.loads(text) == expected

    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            ('effect: x', {'effect': 'x'}),
            ('look-in-dark:', {'look-in-dark': ''}),
            ('\u540d\u524d: x', {'\u540d\u524d': 'x'}),
            ('\u216b: x', {'\u216b': 'x'}),
        ],
    )
    def test_a_key_with_no_uppercase_code_point_still_lexes_as_structure(self, text: str, expected: object) -> None:
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
