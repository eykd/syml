from collections import OrderedDict

from .exceptions import OutOfContextNodeError
from .types import Source
from .utils import get_coords_of_str_index, get_line


class YamlNode:
    def __init__(self, pnode, level=None, parent=None, comments=()):
        self.pnode = pnode
        self._level = None
        self.parent = parent
        self.comments = list(comments)
        self.level = level

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, level):
        self._set_level(level)

    def _set_level(self, level):
        self._level = level

    def as_data(self, filename='', raw=False):
        raise NotImplementedError()

    def get_tip(self):
        return self

    def can_add_node(self, node):
        return False

    def add_node(self, node):
        raise NotImplementedError()

    def incorporate_node(self, node):
        if self.can_add_node(node):
            return self.add_node(node)
        else:
            if self.parent is not None:
                return self.parent.incorporate_node(node)
            else:
                # Shouldn't ever get here:
                self.fail_to_incorporate_node(node)  # pragma: no cover

    def fail_to_incorporate_node(self, node):
        pnode = node.pnode
        pos = get_coords_of_str_index(pnode.full_text, pnode.start)
        line = get_line(pnode.full_text, pos.line)
        raise OutOfContextNodeError("Line %s, column %s:\n%s" % (pos.line, pos.column, line))


class ContainerNode(YamlNode):
    def __init__(self, pnode, value=None, **kwargs):
        self.value = value
        super().__init__(pnode, **kwargs)

    def _set_level(self, level):
        self._level = level
        if isinstance(self.value, YamlNode):
            self.value.level = level

    def as_data(self, filename='', raw=False):
        if isinstance(self.value, YamlNode):
            return self.value.as_data(filename, raw=raw)
        else:
            # Shouldn't ever get here.
            return self.value  # pragma: no cover

    def get_tip(self):
        if self.value is not None and isinstance(self.value, YamlNode):
            return self.value.get_tip()
        else:
            return self

    def incorporate_node(self, node):
        if self.can_add_node(node):
            intermediary = None
            if isinstance(node, KeyValue):
                intermediary = Mapping(node.pnode)
            elif isinstance(node, ListItem):
                intermediary = List(node.pnode)

            if intermediary is not None:
                intermediary.level = node.level
                intermediary = self.incorporate_node(intermediary)
                return intermediary.incorporate_node(node)
            else:
                return super().incorporate_node(node)
        else:
            if self.parent is not None:
                return self.parent.incorporate_node(node)
            else:
                self.fail_to_incorporate_node(node)

    def can_add_node(self, node):
        return (
            self.value is None
            and (
                node.level is None
                or node.level > self.level
            )
        )

    def add_node(self, node):
        self.value = node
        node.parent = self
        if node.level is None:
            node.level = self.level
        return node.get_tip()


class ParentNode(YamlNode):
    def __init__(self, pnode, children=(), **kwargs):
        self.children = list(children)
        super().__init__(pnode, **kwargs)

    def _set_level(self, level):
        self._level = level
        for child in self.children:
            if isinstance(child, YamlNode):
                child.level = level

    def get_tip(self):
        if self.children and isinstance(self.children[-1], YamlNode):
            return self.children[-1].get_tip()
        else:
            return self

    def can_add_node(self, node):
        return node.level is None or node.level >= self.level

    def add_node(self, node):
        self.children.append(node)
        node.parent = self
        if node.level is None:
            node.level = self.level
        return node.get_tip()


class Root(ContainerNode):
    def __init__(self, pnode):
        super().__init__(pnode, level=0)

    def can_add_node(self, node):
        return (
            self.value is None
            and (
                node.level is None
                or node.level >= self.level
            )
        )


class Comment(ContainerNode):
    pass


class List(ParentNode):
    def can_add_node(self, node):
        return (
            super().can_add_node(node)
            and
            isinstance(node, ListItem)
        )

    def as_data(self, filename='', raw=False):
        return [c.as_data(filename, raw=raw) for c in self.children]


class ListItem(ContainerNode):
    pass


class Mapping(ParentNode):
    def can_add_node(self, node):
        return (
            super().can_add_node(node)
            and
            isinstance(node, KeyValue)
        )

    def as_data(self, filename='', raw=False):
        return OrderedDict([
            (c.key.as_data(filename, raw=raw), c.as_data(filename, raw=raw))
            for c in self.children
        ])


class KeyValue(ContainerNode):
    def __init__(self, pnode, key, **kwargs):
        self.key = key
        super().__init__(pnode, **kwargs)


class LeafNode(YamlNode):
    def __init__(self, pnode, source_text, value=None, **kwargs):
        self.source_text = source_text
        self.value = [(pnode, value)] if value is not None else [(pnode, source_text)]
        super().__init__(pnode, **kwargs)

    def as_data(self, filename='', raw=False):
        if raw:
            return self.get_value()
        else:
            start_pnode = self.value[0][0]
            end_pnode = self.value[-1][0]
            start = get_coords_of_str_index(start_pnode.full_text, start_pnode.start)
            end = get_coords_of_str_index(end_pnode.full_text, end_pnode.end)

            return Source(
                filename = filename,
                start = start,
                end = end,
                text = self.source_text,
                # Values correspond to lines of text
                value = self.get_value(),
            )

    def can_add_node(self, node):
        return (
            isinstance(node, LeafNode)
            and (
                node.level is None
                or node.level >= self.level
            )
        )


class TextLeafNode(LeafNode):
    def add_node(self, node):
        self.source_text += '\n' + node.get_value()
        self.value.extend(node.value)
        node.parent = self
        return self.get_tip()

    def get_value(self):
        return '\n'.join([v[1] for v in self.value])


class RawValueLeafNode(LeafNode):
    def get_value(self):
        return self.value[0][1]
