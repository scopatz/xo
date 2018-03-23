#! /usr/bin/env python

import sys
#try:
#    from setuptools import setup
#    have_setuptools = True
#except ImportError:
#    from distutils.core import setup
#    have_setuptools = False

# setuptools no longer works.
from distutils.core import setup
have_setuptools = False

if sys.version_info[0] < 3:
    sys.exit("ERROR: xo requires Python 3.")

VERSION = '0.2.1'

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
    }

if have_setuptools:
    setup_kwargs['install_requires'] = [
        'Pygments >= 1.6',
        'urwid >= 1.1.1',
        ]
    setup_kwargs["zip_safe"] = False

if __name__ == '__main__':
    setup(
        name='exofrills',
        py_modules=['xo'],
        packages=['xontrib'],
        scripts=['xo'],
        long_description=open('readme.rst').read(),
        **setup_kwargs
        )
