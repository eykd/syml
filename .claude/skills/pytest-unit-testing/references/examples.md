# Example Tests

These examples were run against the real `syml` API with
`uv run pytest <file> --no-cov -p no:random_order` and pass. They show the
class-based grouping, `test_it_should_...` naming, full type annotations,
`pytest.mark.parametrize`, and `pytest.raises(..., match=...)` conventions
described in `SKILL.md`.

## A Simple Direct Assertion

```python
import syml


class TestLoadsSimpleValue:
    def test_it_should_load_a_single_key_value_mapping(self) -> None:
        result = syml.loads('name: syml')
        assert result == {'name': 'syml'}
```

## Parametrized Cases

```python
from typing import Any

import pytest

import syml


class TestLoadsParametrized:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            ('foo: bar', {'foo': 'bar'}),
            ('- foo\n- bar\n', ['foo', 'bar']),
            ('just text', 'just text'),
        ],
    )
    def test_it_should_load_various_shapes(self, text: str, expected: Any) -> None:
        assert syml.loads(text) == expected
```

Each row becomes its own test id in `-vv` output
(`test_it_should_load_various_shapes[foo: bar-expected0]`, etc.), so a
failure names the exact input that broke.

## Asserting a Raised Exception with `match=`

```python
import pytest

import syml
from syml.exceptions import OutOfContextNodeError


class TestOutOfContextError:
    def test_it_should_raise_on_a_bad_dedent(self) -> None:
        text = '  - foo:\n      - bar\n - baz\n- blah\n'
        with pytest.raises(OutOfContextNodeError, match='line=3'):
            syml.loads(text)
```

`OutOfContextNodeError`'s message embeds the `Pos` where incorporation
failed (`Pos(index=..., line=3, column=...)`), which is why `match='line=3'`
pins the assertion to the specific line the malformed document breaks on,
not just "some `OutOfContextNodeError` was raised somewhere."

## Asserting on `Source` / `Pos` (the source-tracking API)

```python
from syml.basetypes import Pos, Source


class TestSourceTracking:
    def test_it_should_track_source_position_for_a_value(self) -> None:
        text = 'name: syml\n'
        result = syml.parsers.parse(text).as_source()
        assert result == {Source.from_text(text, 'name'): Source.from_text(text, 'syml')}

    def test_it_should_expose_pos_fields_on_source(self) -> None:
        text = 'name: syml\n'
        source = Source.from_text(text, 'syml')
        assert isinstance(source.start, Pos)
        assert source.start.line == 1
```

`Source.from_text(text, substring)` (used throughout `tests/test_parsers.py`)
builds the expected `Source` by locating `substring` inside `text`, which is
easier to read and maintain than hand-computing `Pos(index=..., line=...,
column=...)` for every expected value. Reach for `Source.from_node` only when
a test already has a real `parsimonious.nodes.Node` in hand (rare outside
`parsers.py`/`nodes.py` themselves).
