from funcy import memoize


@memoize
def split_lines(text, keepends=False):
    return text.splitlines(keepends=keepends)


def get_line(text: str, line_number: int) -> str:
    try:
        return split_lines(text, True)[line_number - 1]
    except IndexError:
        return ""
