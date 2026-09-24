from syml import preprocess


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
