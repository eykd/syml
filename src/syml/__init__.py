from . import _version, parser

__version__: str = _version.get_versions()["version"]  # type: ignore


def loads(document, **kwargs):
    return parser.parse(document, **kwargs)


def load(file_obj, **kwargs):
    return loads(file_obj.read(), **kwargs)
