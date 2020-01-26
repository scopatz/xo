#! /usr/bin/env python

import sys

# setuptools no longer works.
from distutils.core import setup

if sys.version_info[0] < 3:
    sys.exit("ERROR: xo requires Python 3.")

VERSION = '0.3.3'

setup_kwargs = {
    "version": VERSION,
    "description": 'exofrills text editor',
    "author": 'Anthony Scopatz',
    "author_email": 'scopatz@gmail.com',
    "url": 'http://exofrills.org/',
    "download_url": "https://github.com/scopatz/xo/zipball/" + VERSION,
    "classifiers": [
        "License :: OSI Approved",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Topic :: Utilities",
        "Topic :: Text Editors",
        ],
    "data_files": [("", ['license', 'readme.rst']),],
    "install_requires": [
        'Pygments >= 1.6',
        'urwid >= 1.1.1',
        'pygments_cache',
        ],
    "zip_safe": False,
    }

if __name__ == '__main__':
    setup(
        name='exofrills',
        py_modules=['xo'],
        packages=['xontrib'],
        scripts=['xo'],
        long_description=open('readme.rst').read(),
        **setup_kwargs
        )
