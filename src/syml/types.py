import attr


@attr.s(slots=True, frozen=True)
class Pos:
    index = attr.ib()
    line = attr.ib()
    column = attr.ib()


@attr.s(slots=True, repr=False, frozen=True)
class Source:
    filename = attr.ib()
    start = attr.ib()
    end = attr.ib()
    text = attr.ib()
    value = attr.ib()

    def __repr__(self):
        return '%sLine %s, Column %s (index %s): %r (%r)' % (
            '%s, ' % self.filename if self.filename else '',
            self.start.line, self.start.column, self.start.index, self.text, self.value,
        )
