xo: the text editor without frills
==================================
You might be looking for help, but this is all I can do::

    usage: xo [-h] path

    exofrills: your text has been edited...but you are still hungry.

    positional arguments:
      path        path to file, may include colon separated line and col numbers,
                  eg 'path/to/xo.py:10:42'

    optional arguments:
      -h, --help  show this help message and exit

Someone else made a `video tutorial <http://youtu.be/bPq8fncImtQ>`_ and posted 
it on YouTube within an hour of the 0.1 release.

get xo
------
Install from the cheeese shop with ``pip`` or ``easy_install``:

.. code-block:: bash

    $ pip install exofrills

.. code-block:: bash

    $ easy_install exofrills

Fork xo from `github <https://github.com/scopatz/xo>`_:

.. code-block:: bash

    $ git clone https://github.com/scopatz/xo.git


key commands
------------
:esc: get help
:ctrl + o: save file (write-out)
:ctrl + x: exit (does not save)

:meta + s: select pygments style
:ctrl + f: insert file at current position
:ctrl + y: go to line & column (yalla, let's bounce)

:ctrl + k: cuts the current line to the clipboard
:ctrl + u: pastes the clipboard to the current line
:ctrl + t: clears the clipboard (these spell K-U-T)

:ctrl + w: set regular expression and jump to first match
:meta + w: jump to next match of current regular expression
:ctrl + r: set substitution for regular expression and replace first match
:meta + r: replace next match of current regular expression

