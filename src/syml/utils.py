from .types import Pos


def get_coords_of_str_index(text: str, index: int) -> Pos:
    """Get (line_number, col) of `index` in `string`.

    Based on http://stackoverflow.com/a/24495900
    """
    return Pos.from_str_index(text, index)


def get_line(text: str, line_number: int) -> str:
    try:
        return text.splitlines(True)[line_number - 1]
    except IndexError:
        return ""
