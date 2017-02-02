"""Exofrills xontrib."""
from xonsh.proc import unthreadable, uncapturable
from xo import main as _main

@unthreadable
@uncapturable
def _xo(args, stdin=None):
    _main(args=args)


aliases['xo'] = _xo
del unthreadable, uncapturable
