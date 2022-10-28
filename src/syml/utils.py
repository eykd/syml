from typing import Optional

from .types import Pos, Source


def get_coords_of_str_index(text: str, index: int) -> Pos:
    """Get (line_number, col) of `index` in `string`.

    Based on http://stackoverflow.com/a/24495900
    """
    lines = text.splitlines(True)
    curr_pos = 0
    for linenum, line in enumerate(lines):
        if curr_pos + len(line) > index:
            return Pos(index, linenum + 1, index - curr_pos)
        curr_pos += len(line)
    return Pos(len(text), linenum + 1, 0)


def get_line(text: str, line_number: int) -> str:
    try:
        return text.splitlines(True)[line_number - 1]
    except IndexError:
        return ""


def get_text_source(
    text: str, substring: str = None, source_text: Optional[str] = None, value: Optional[str] = None, filename: str = ""
) -> Source:
    return Source.from_text(text, substring, source_text, value, filename)
