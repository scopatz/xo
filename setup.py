try:
    from setuptools import setup
    have_setuptools = True
except ImportError:
    from distutils.core import setup
    have_setuptools = False

VERSION = "0.1"

setup_kwargs = {
    "version": VERSION,
    "description": 'exofrills text editor',
    "author": 'Anthony Scopatz',
    "author_email": 'scopatz@gmail.com',
    "url": 'http://exofrills.org/',
    "download_url": "https://github.com/scopatz/xo/zipball/" + VERSION,
    "classifiers": [
        "License :: OSI Approved :: BSD License",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Topic :: Utilities",
        "Topic :: Software Development :: Build Tools",
        ],
    "zip_safe": False,
    }

if have_setuptools:
    setup_kwargs['install_requires'] = [
        'Pygments >= 1.6',
        ]
setup(
    name='exofrills',
    py_modules=['xo'],
    entry_points={'console_scripts': ['xo = xo:main',],},
    long_description=open('readme.rst').read(),
    **setup_kwargs
    )

