import re
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
    text: str, substring: str, source_text: Optional[str] = None, value: Optional[str] = None, filename: str = ""
) -> Source:
    match = re.search(substring, text)
    if match is None:
        raise ValueError(f"No match found for {substring!r}")
    source_text = match.group() if source_text is None else source_text
    return Source(
        filename=filename,
        start=get_coords_of_str_index(text, match.start()),
        end=get_coords_of_str_index(text, match.end()),
        text=source_text,
        value=value if value is not None else source_text,
    )
