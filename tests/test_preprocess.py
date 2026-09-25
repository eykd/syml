import pytest

from syml import preprocess
from syml.basetypes import Pos
from syml.exceptions import TabIndentationError
from syml.preprocess import PositionMap


class TestPreprocessBomStripping:
    def test_it_should_strip_exactly_one_leading_bom(self) -> None:
        document = preprocess.preprocess('﻿key: value')

        assert document.normalized == 'key: value'
        assert document.position_map.bom_offset == 1


class TestPositionMapLine1BomOffset:
    """`PositionMap.line1_bom_offset` (D33, syml-cjk2.17)."""

    def test_it_should_return_the_bom_offset_on_line_1(self) -> None:
        position_map = PositionMap(bom_offset=1, crlf_indices=())

        assert PositionMap.line1_bom_offset(position_map, 1) == 1

    def test_it_should_return_zero_off_line_1(self) -> None:
        position_map = PositionMap(bom_offset=1, crlf_indices=())

        assert PositionMap.line1_bom_offset(position_map, 2) == 0

    def test_it_should_return_zero_with_no_position_map(self) -> None:
        assert PositionMap.line1_bom_offset(None, 1) == 0


class TestPreprocessLineEndings:
    def test_it_should_normalize_line_endings_to_lf(self) -> None:
        document = preprocess.preprocess('a: b\r\nc: d')
        assert document.normalized == 'a: b\nc: d'
        assert document.position_map.crlf_indices == (4,)

        document = preprocess.preprocess('a: b\rc: d')
        assert document.normalized == 'a: b\nc: d'
        assert document.position_map.crlf_indices == ()

        document = preprocess.preprocess('a: b\r\r\nc')
        assert document.normalized == 'a: b\n\nc'
        assert document.position_map.crlf_indices == (5,)

        document = preprocess.preprocess('a: b\r')
        assert document.normalized == 'a: b\n'
        assert document.position_map.crlf_indices == ()


class TestPreprocessBlankClassificationAndTabScan:
    def test_it_should_raise_tab_indentation_error_for_a_leading_tab_but_not_for_a_blank_line(
        self,
    ) -> None:
        with pytest.raises(TabIndentationError):
            preprocess.preprocess('\tkey: value')

        # A tab-bearing line with nothing else on it is blank (§4.4, D14) and
        # is exempt from the tab scan entirely.
        document = preprocess.preprocess('  \t  \nkey: v')
        assert document.normalized == '  \t  \nkey: v'


class TestTabIndentationErrorFilename:
    """TabIndentationError carries the filename prefix like every other ParseError (syml-xreq.4)."""

    def test_it_should_prefix_message_and_str_with_the_given_filename(self) -> None:
        with pytest.raises(TabIndentationError) as exc_info:
            preprocess.preprocess('a:\n\tb: 1', filename='f.syml')

        assert exc_info.value.message.startswith('f.syml: ')
        assert str(exc_info.value).startswith('f.syml:')


class TestTabIndentationErrorOriginalTextPosition:
    """TabIndentationError.position reports original-text coordinates (FR-013, US2-12/13/14)."""

    def test_it_should_report_the_original_index_through_a_crlf_collapse(self) -> None:
        with pytest.raises(TabIndentationError) as exc_info:
            preprocess.preprocess('a: 1\r\n\tb: 2')

        assert exc_info.value.position == Pos(6, 2, 0)

    def test_it_should_report_the_original_index_through_a_bom(self) -> None:
        with pytest.raises(TabIndentationError) as exc_info:
            preprocess.preprocess('﻿\tk: v')

        assert exc_info.value.position == Pos(1, 1, 1)

    def test_it_should_report_the_original_index_through_a_bom_and_a_crlf_collapse(self) -> None:
        with pytest.raises(TabIndentationError) as exc_info:
            preprocess.preprocess('﻿a: b\r\n\tc: d')

        assert exc_info.value.position == Pos(7, 2, 0)

    def test_it_should_center_the_excerpt_window_the_same_with_or_without_a_bom(self) -> None:
        """`str(e)`'s excerpt line is BOM-independent on a long BOM-led line 1 (D33, syml-cjk2.17).

        Padding after the tab (not just before it) keeps the window's end
        away from `len(line_text)`, so a naive fix that only clamps against
        the end of the line can't accidentally pass this by coincidence.
        """
        line = ' ' * 100 + '\t' + 'x' * 100
        with pytest.raises(TabIndentationError) as with_bom:
            preprocess.preprocess('﻿' + line)
        with pytest.raises(TabIndentationError) as without_bom:
            preprocess.preprocess(line)

        assert str(with_bom.value).splitlines()[1] == str(without_bom.value).splitlines()[1]

    def test_it_should_not_raise_when_a_tab_follows_a_nonbreakingspaceled_line(self) -> None:
        # A NBSP-led line is content at column 0, not indentation (D14): the
        # leading-whitespace run before its first tab is empty, so the tab
        # scan never sees it as indentation.
        document = preprocess.preprocess('key: v\n\xa0\tx')

        assert document.normalized == 'key: v\n\xa0\tx'


class TestPositionMapToOriginal:
    def test_it_should_map_normalized_positions_back_to_original_via_bisect_left(
        self,
    ) -> None:
        # BOM offset: normalized Pos of `value` -> original Pos shifted by 1.
        document = preprocess.preprocess('﻿key: value')
        assert document.position_map.to_original(Pos(5, 1, 5)) == Pos(6, 1, 6)

        # CRLF collapse: a position at the collapsed break bisects left onto
        # the `\r`, the first character of the original break.
        document = preprocess.preprocess('a: b\r\nc: d')
        assert document.position_map.to_original(Pos(5, 2, 0)) == Pos(6, 2, 0)
        assert document.position_map.to_original(Pos(4, 1, 4)) == Pos(4, 1, 4)
