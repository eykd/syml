import textwrap
from io import StringIO

import pytest
from parsimonious import Grammar
from parsimonious.expressions import Literal
from parsimonious.nodes import Node

import syml
from syml import exceptions, parsers, quoting
from syml.basetypes import Source


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

        A zero-length *unquoted* inline value is normalized to "no inline
        value at all", identical to ``key:`` with nothing after it -- the
        node stays open and accepts the following nested block instead of
        treating the empty text as the value.
        """
        text = 'key: \n  nested: content'
        result = parser.parse(text)
        assert result.as_data() == {'key': {'nested': 'content'}}

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


class TestFindFirst:
    """Contract 05 §The third-party boundary (FR-009, R-09): the `find_first` helper.

    `raise_trailing_content` uses `find_first` to locate the `quoted_value`
    node that anchors a stranded-content error at the opening quote, since
    parsimonious's `Node` has no such lookup itself.
    """

    def test_find_first_returns_the_first_matching_node_in_depth_first_order(self) -> None:
        """It must return the nested, document-first match — not the root, and not by luck."""
        grammar = Grammar(
            r"""
            root         = wrapper other
            wrapper      = quoted_value / other_char
            other_char   = ~"Z"
            quoted_value = ~"Q\d"
            other        = quoted_value / other_char
            """
        )
        tree = grammar['root'].parse('Q1Q2')
        expected = tree.children[0].children[0]
        assert expected.expr_name == 'quoted_value'

        result = parsers.find_first(tree, 'quoted_value')

        assert result is expected


class TestVisitQuotedValueDecoderDefectConversion:
    """Contract 05 §Decoder failures cross the visitor as `ParseError`s.

    `decode_double_quoted` is position-free and raises the module-private
    `quoting.QuotedStringDefect`; `visit_quoted_value` is the only place that
    catches it and re-raises `MalformedQuotedStringError`, and that
    conversion must reach `parser.visit()` **unwrapped** — not
    `parsimonious.exceptions.VisitationError` — because Parsimonious wraps
    exceptions raised while visiting a node before the parent's own
    `visit_*` runs (§ Why not in `visit_key_value` / `visit_list_item`).
    """

    def test_a_decoder_defect_crosses_the_visitor_as_a_malformed_quoted_string_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A surrogate escape's `QuotedStringDefect` must surface as `MalformedQuotedStringError`.

        Patches the *module attribute* `quoting.decode_double_quoted`, not
        the name imported into `parsers` — Green must call it via
        `quoting.decode_double_quoted(...)` (`from . import quoting`) for
        this patch to take effect (a `from .quoting import
        decode_double_quoted` binding would not be patched by this).
        """
        raw = '"\\ud800"'
        node = Node(Literal(raw, name='quoted_value'), raw, 0, len(raw))

        def fake_decode_double_quoted(_raw: str) -> str:
            raise quoting.QuotedStringDefect(escape='\\ud800', code_point=0xD800)

        monkeypatch.setattr(quoting, 'decode_double_quoted', fake_decode_double_quoted)

        parser = parsers.SymlParser()

        with pytest.raises(exceptions.MalformedQuotedStringError) as excinfo:
            parser.visit(node)

        assert excinfo.value.escape == '\\ud800'
        assert excinfo.value.code_point == 0xD800
        assert isinstance(excinfo.value.__cause__, quoting.QuotedStringDefect)
