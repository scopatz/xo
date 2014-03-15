.. raw:: html

    <link href="_static/unicodetiles.css" rel="stylesheet" type="text/css" />
    <script src="_static/unicodetiles.min.js"></script>
    <script src="_static/xo-dungeon.js"></script>
    <div style="text-align:center;">
        <div id="game"><h1>welcome to the xo docs</h1></div>
    </div>
    <script type="text/javascript">initXoDungeon();</script>

exofrills - when ``nano`` is too much
=====================================
Have you ever been frustrated that your text editor wasn't doing what you wanted?
Angered that you can't remember...

* ...how to find help? 
* ...what ``:wq`` means? 
* ...any of the little lisper that you read as an undergrad?

A small, brave world awaits!

-----------

.. raw:: html

    <div style="text-align:right;">
        <img src="_static/whatis.png">
    </div>

brutally lightweight
====================
The exofrills (``xo``, pronounced 'ex-oh') text editor is designed to just provide 
the features that you need to program effectively and nothing else. It is *ridiculously* lightweight
and only relies on Python 3, `urwid <http://urwid.org/>`_, and 
`pygments <http://pygments.org/>`_.

**Current Features:**

    * Less than 850 lines of code in a single file!
    * Syntax highlighting!
    * Regular expression matching and replacing!
    * Search history caching!
    * WTFPL licensed!
    * Fully customizable!
    * Start at non-origin locations!
    * Hop between words on a line!
    * Jump to anywhere in the file!
    * Whole file insertion!
    * Beginner friendly - maybe you are new to words!
    * Copy and paste text!
    * Line and column status!
    * Only one row of non-text editing space!
    * Both saving & loading!

If you ask for more features *I will probably say no!* Just fork xo yourself.

**Writing text editors is not hard!**  Make one your own today.

-----------

.. raw:: html

    <div style="text-align:right;">
        <img src="_static/50less.png">
    </div>

**exofrills now has 50% less characters in its name than other industry leaders!**

====== ===== ====== ===== ====== ===== ====== =====
vi     2     vim    3     nano   4     pico   4
**xo** **2** cat    3     less   4     emacs  5
====== ===== ====== ===== ====== ===== ====== =====

-----------

.. raw:: html


    <div style="text-align:right;">
        <img src="_static/whatin.png">
    </div>
    <br />
    <div style="text-align:left;">
        <img src="_static/xo.png">
    </div>
    <br />
    <div style="text-align:right;">
        <img src="_static/srsly.png">
    </div>
    <br />
    <div style="text-align:left;">
        <img src="_static/yes-xo.png">
    </div>
    <br />
    <div style="text-align:right;">
        <img src="_static/damn.png">
    </div>

-----------

get xo
======
Install from the cheeese shop with ``pip`` or ``easy_install``:

.. code-block:: bash

    $ pip install exofrills

.. code-block:: bash

    $ easy_install exofrills

Fork xo from `github <https://github.com/scopatz/xo>`_:

.. code-block:: bash

    $ git clone https://github.com/scopatz/xo.git

-----------

key commands
============
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

-----------

~xo <A3


