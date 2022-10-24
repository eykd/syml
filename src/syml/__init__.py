from . import _version, parser

__version__ = _version.get_versions()["version"]


def loads(document, **kwargs):
    return parser.parse(document, **kwargs)


def load(file_obj, **kwargs):
    return loads(file_obj.read(), **kwargs)
