import pytest

from syml import preprocess
from syml.basetypes import Pos
from syml.exceptions import TabIndentationError


class TestPreprocessBomStripping:
    def test_it_should_strip_exactly_one_leading_bom(self) -> None:
        document = preprocess.preprocess('﻿key: value')

        assert document.normalized == 'key: value'
        assert document.position_map.bom_offset == 1


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


class TestSplitLinesLf:
    def test_it_should_split_only_on_lf_not_other_unicode_line_terminators(self) -> None:
        assert preprocess.split_lines_lf('a: b c\nx: y') == [  # noqa: RUF001
            'a: b c',  # noqa: RUF001
            'x: y',
        ]


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
