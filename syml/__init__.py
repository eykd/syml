from . import parser


def loads(document, **kwargs):
    return parser.parse(document, **kwargs)


def load(file_obj, **kwargs):
    return loads(file_obj.read(), **kwargs)
