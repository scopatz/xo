"""Exofrills xontrib."""
from xonsh.proc import foreground
from xo import main as _main

@foreground
def _xo(args, stdin=None):
    _main(args=args)


aliases['xo'] = _xo
del foreground
