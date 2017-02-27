# -*- coding: utf-8 -*-
from setuptools import setup

PROJECT_NAME = 'syml'
VERSION = '0.1.dev0'

setup(
    name = PROJECT_NAME,
    version = VERSION,
    author = "David Eyk",
    author_email = "david.eyk@gmail.com",
    modules = [PROJECT_NAME],
    install_requires = [
        'attrs==16.2.0',
        'parsimonious==0.7.0',
    ],
    entry_points = dict(
        console_scripts = [
            'ravel = ravel.cli:main',
        ]
    ),
)
