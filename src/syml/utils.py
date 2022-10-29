from funcy import memoize

from .types import Pos


@memoize
def split_lines(text, keepends=False):
    return text.splitlines(keepends=keepends)


def get_coords_of_str_index(text: str, index: int) -> Pos:
    """Get (line_number, col) of `index` in `string`.

    Based on http://stackoverflow.com/a/24495900
    """
    return Pos.from_str_index(text, index)


def get_line(text: str, line_number: int) -> str:
    try:
        return split_lines(text, True)[line_number - 1]
    except IndexError:
        return ""
