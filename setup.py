from setuptools import setup

setup(
    name='exofrills',
    py_modules=['xo'],
    entry_points={
        'console_scripts': ['xo = xo:main', ],},
    long_description=open('readme.rst').read(),
)
