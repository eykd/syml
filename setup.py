# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
import versioneer


with open('README.rst') as README:
    setup(
        name = 'syml',
        version=versioneer.get_version(),
        author = "David Eyk",
        author_email = "david.eyk@gmail.com",
        cmdclass=versioneer.get_cmdclass(),
        description = (
            "SYML (Simple YAML-like Markup Language) is a simple markup "
            "language with similar structure to YAML, but without all the gewgaws "
            "and folderol."
        ),
        long_description = README.read(),
        url = 'https://github.com/eykd/syml',
        license = 'MIT',
        packages = find_packages(),
        install_requires = [
            'attrs<17',
            'parsimonious<0.8',
        ],
        keywords = ['yaml', 'markup', 'syml'],
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Intended Audience :: Developers',
            'Programming Language :: Python :: 3.5',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Topic :: Text Processing :: Markup',
        ],
    )
