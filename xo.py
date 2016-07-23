#!/usr/bin/env python3
"""exofrills: your text has been edited...but you are still hungry.

key commands
------------
esc: get help
{save}: save file (write-out)
{exit}: exit (does not save)

{style}: select pygments style
{insert}: insert file at current position
{jump}: go to line & column (yalla, let's bounce)

{cut}: cuts the current line to the clipboard
{paste}: pastes the clipboard to the current line
{clear_clipboard}: clears the clipboard (these spell K-U-T by default)

{find}: set regular expression and jump to first match
{find_next}: jump to next match of current regular expression
{replace}: set substitution for regular expression and replace first match
{replace_next}: replace next match of current regular expression
"""
import os
import re
import io
import sys
import json
import time
from glob import glob
from itertools import zip_longest
from collections import deque, Mapping, Sequence
from argparse import ArgumentParser, RawDescriptionHelpFormatter

# must come before pygments imports
from lazyasd import load_module_in_background
load_module_in_background('pkg_resources',
                          replacements={'pygments.plugin': 'pkg_resources'})

import urwid
import pygments.util
from pygments.lexers import guess_lexer, guess_lexer_for_filename, get_lexer_by_name
from pygments.lexers.special import TextLexer
from pygments.lexers.python import PythonLexer, Python3Lexer
from pygments.token import Token
from pygments.filter import Filter
from pygments.styles import get_all_styles, get_style_by_name

__version__ = '0.1.13'

RE_WORD = re.compile(r'\w+')
RE_NOT_WORD = re.compile(r'\W+')
RE_NOT_SPACE = re.compile(r'\S')
RE_TWO_DIGITS = re.compile("(\d+)(\D+)?(\d+)?")
RE_SPACES = re.compile(r'( +)')

RC_PATH = os.path.expanduser('~/.config/xo/rc.json')
DEFAULT_RC = {
    'queries': [],
    'replacements': [],
    'max_queries': 128,
    'max_replacements': 128,
    'tabs': {
        # name: (size, must_retab)
        'default': (4, False),
        'c': (2, False),
        'h': (2, False),
        'cc': (2, False),
        'c++': (2, False),
        'h++': (2, False),
        'cpp': (2, False),
        'hpp': (2, False),
        'cxx': (2, False),
        'hxx': (2, False),
        'tsv': (8, True),
        'Makefile': (4, True),
        },
    'style': 'monokai',
    'short_to_rgb': {  # color look-up table for 8-bit to RGB hex
        # Primary 3-bit (8 colors). Unique representation!
        '00': '000000', '01': '800000', '02': '008000', '03': '808000', '04': '000080',
        '05': '800080', '06': '008080', '07': 'c0c0c0',
        # Equivalent "bright" versions of original 8 colors.
        '08': '808080', '09': 'ff0000', '10': '00ff00', '11': 'ffff00', '12': '0000ff',
        '13': 'ff00ff', '14': '00ffff', '15': 'ffffff',
        # Strictly ascending.
        '16': '000000', '17': '00005f', '18': '000087', '19': '0000af', '20': '0000d7',
        '21': '0000ff', '22': '005f00', '23': '005f5f', '24': '005f87', '25': '005faf',
        '26': '005fd7', '27': '005fff', '28': '008700', '29': '00875f', '30': '008787',
        '31': '0087af', '32': '0087d7', '33': '0087ff', '34': '00af00', '35': '00af5f',
        '36': '00af87', '37': '00afaf', '38': '00afd7', '39': '00afff', '40': '00d700',
        '41': '00d75f', '42': '00d787', '43': '00d7af', '44': '00d7d7', '45': '00d7ff',
        '46': '00ff00', '47': '00ff5f', '48': '00ff87', '49': '00ffaf', '50': '00ffd7',
        '51': '00ffff', '52': '5f0000', '53': '5f005f', '54': '5f0087', '55': '5f00af',
        '56': '5f00d7', '57': '5f00ff', '58': '5f5f00', '59': '5f5f5f', '60': '5f5f87',
        '61': '5f5faf', '62': '5f5fd7', '63': '5f5fff', '64': '5f8700', '65': '5f875f',
        '66': '5f8787', '67': '5f87af', '68': '5f87d7', '69': '5f87ff', '70': '5faf00',
        '71': '5faf5f', '72': '5faf87', '73': '5fafaf', '74': '5fafd7', '75': '5fafff',
        '76': '5fd700', '77': '5fd75f', '78': '5fd787', '79': '5fd7af', '80': '5fd7d7',
        '81': '5fd7ff', '82': '5fff00', '83': '5fff5f', '84': '5fff87', '85': '5fffaf',
        '86': '5fffd7', '87': '5fffff', '88': '870000', '89': '87005f', '90': '870087',
        '91': '8700af', '92': '8700d7', '93': '8700ff', '94': '875f00', '95': '875f5f',
        '96': '875f87', '97': '875faf', '98': '875fd7', '99': '875fff', '100': '878700',
        '101': '87875f', '102': '878787', '103': '8787af', '104': '8787d7',
        '105': '8787ff', '106': '87af00', '107': '87af5f', '108': '87af87',
        '109': '87afaf', '110': '87afd7', '111': '87afff', '112': '87d700',
        '113': '87d75f', '114': '87d787', '115': '87d7af', '116': '87d7d7',
        '117': '87d7ff', '118': '87ff00', '119': '87ff5f', '120': '87ff87',
        '121': '87ffaf', '122': '87ffd7', '123': '87ffff', '124': 'af0000',
        '125': 'af005f', '126': 'af0087', '127': 'af00af', '128': 'af00d7',
        '129': 'af00ff', '130': 'af5f00', '131': 'af5f5f', '132': 'af5f87',
        '133': 'af5faf', '134': 'af5fd7', '135': 'af5fff', '136': 'af8700',
        '137': 'af875f', '138': 'af8787', '139': 'af87af', '140': 'af87d7',
        '141': 'af87ff', '142': 'afaf00', '143': 'afaf5f', '144': 'afaf87',
        '145': 'afafaf', '146': 'afafd7', '147': 'afafff', '148': 'afd700',
        '149': 'afd75f', '150': 'afd787', '151': 'afd7af', '152': 'afd7d7',
        '153': 'afd7ff', '154': 'afff00', '155': 'afff5f', '156': 'afff87',
        '157': 'afffaf', '158': 'afffd7', '159': 'afffff', '160': 'd70000',
        '161': 'd7005f', '162': 'd70087', '163': 'd700af', '164': 'd700d7',
        '165': 'd700ff', '166': 'd75f00', '167': 'd75f5f', '168': 'd75f87',
        '169': 'd75faf', '170': 'd75fd7', '171': 'd75fff', '172': 'd78700',
        '173': 'd7875f', '174': 'd78787', '175': 'd787af', '176': 'd787d7',
        '177': 'd787ff', '178': 'd7af00', '179': 'd7af5f', '180': 'd7af87',
        '181': 'd7afaf', '182': 'd7afd7', '183': 'd7afff', '184': 'd7d700',
        '185': 'd7d75f', '186': 'd7d787', '187': 'd7d7af', '188': 'd7d7d7',
        '189': 'd7d7ff', '190': 'd7ff00', '191': 'd7ff5f', '192': 'd7ff87',
        '193': 'd7ffaf', '194': 'd7ffd7', '195': 'd7ffff', '196': 'ff0000',
        '197': 'ff005f', '198': 'ff0087', '199': 'ff00af', '200': 'ff00d7',
        '201': 'ff00ff', '202': 'ff5f00', '203': 'ff5f5f', '204': 'ff5f87',
        '205': 'ff5faf', '206': 'ff5fd7', '207': 'ff5fff', '208': 'ff8700',
        '209': 'ff875f', '210': 'ff8787', '211': 'ff87af', '212': 'ff87d7',
        '213': 'ff87ff', '214': 'ffaf00', '215': 'ffaf5f', '216': 'ffaf87',
        '217': 'ffafaf', '218': 'ffafd7', '219': 'ffafff', '220': 'ffd700',
        '221': 'ffd75f', '222': 'ffd787', '223': 'ffd7af', '224': 'ffd7d7',
        '225': 'ffd7ff', '226': 'ffff00', '227': 'ffff5f', '228': 'ffff87',
        '229': 'ffffaf', '230': 'ffffd7', '231': 'ffffff',
        # Gray-scale range.
        '232': '080808', '233': '121212', '234': '1c1c1c', '235': '262626',
        '236': '303030', '237': '3a3a3a', '238': '444444', '239': '4e4e4e',
        '240': '585858', '241': '626262', '242': '6c6c6c', '243': '767676',
        '244': '808080', '245': '8a8a8a', '246': '949494', '247': '9e9e9e',
        '248': 'a8a8a8', '249': 'b2b2b2', '250': 'bcbcbc', '251': 'c6c6c6',
        '252': 'd0d0d0', '253': 'dadada', '254': 'e4e4e4', '255': 'eeeeee',
        },
    'keybindings': {
        "save": "ctrl o",
        "exit": "ctrl x",
        "cut": "ctrl k",
        "paste": "ctrl u",
        "clear_clipboard": "ctrl t",
        "jump": "ctrl y",
        "insert": "ctrl f",
        "style": "meta s",
        "find": "ctrl w",
        "find_next": "meta w",
        "replace": "ctrl r",
        "replace_next": "meta r",
        },
    'multiline_window': 750,  # this is good size to balance response vs long comments
    'number_of_windows': 1,   # maximum nuber of windows to pane.
    }
DEFAULT_RC['rgb_to_short'] = {v: k for k, v in DEFAULT_RC['short_to_rgb'].items()}

def merge_value(v1, v2):
    if isinstance(v1, Mapping):
        v = {}
        v.update(v1)
        v.update(v2)
    elif isinstance(v1, str):
        v = v2
    elif isinstance(v1, Sequence):
        v = list(v1) + list(v2)
    else:
        v = v2
    return v

def merge_rcs(rc1, rc2):
    rc = {}
    for k, v1 in rc1.items():
        rc[k] = merge_value(v1, rc2[k]) if k in rc2 else v1
    for k, v2 in rc2.items():
        if k not in rc1:
            rc[k] = v2
    return rc

def json_rc_load(fname):
    fname = os.path.expanduser(fname)
    if not os.path.isfile(fname):
        return {}
    with open(fname) as f:
        try:
            rc = json.load(f)
        except ValueError:
            print("Warning: rc file not valid JSON.", file=sys.stderr)
            rc = {}
    return rc

def rgb_to_short(rgb, mapping):
    """Find the closest xterm-256 approximation to the given RGB value."""
    # Thanks to Micah Elliott (http://MicahElliott.com) for colortrans.py
    rgb = rgb.lstrip('#') if rgb.startswith('#') else rgb
    incs = (0x00, 0x5f, 0x87, 0xaf, 0xd7, 0xff)
    # Break 6-char RGB code into 3 integer vals.
    parts = [int(h, 16) for h in re.split(r'(..)(..)(..)', rgb)[1:4]]
    res = []
    for part in parts:
        i = 0
        while i < len(incs)-1:
            s, b = incs[i], incs[i+1]  # smaller, bigger
            if s <= part <= b:
                s1 = abs(s - part)
                b1 = abs(b - part)
                if s1 < b1: closest = s
                else: closest = b
                res.append(closest)
                break
            i += 1
    res = ''.join([ ('%02.x' % i) for i in res ])
    equiv = mapping[res]
    return equiv, res

class NonEmptyFilter(Filter):
    """Ensures that tokens have len > 0."""
    def filter(self, lexer, stream):
        for ttype, value in stream:
            if len(value) > 0:
                yield ttype, value

def sanitize_text(t, tabsize):
    if t.endswith('\n'):
        t = t[:-1]
    t = t.expandtabs(tabsize)
    return t

class LineEditor(urwid.Edit):
    """Line editor with highligthing, column numbering, and smart home."""
    def __init__(self, edit_text="", lexer=None, main_display=None, smart_home=True,
                 tabsize=None, **kwargs):
        self.original_text = edit_text
        super().__init__(edit_text=sanitize_text(edit_text, tabsize), **kwargs)
        if lexer is None:
            lexer = guess_lexer(self.get_edit_text())
        self.lexer = lexer
        self.tabsize = tabsize
        self.main_display = main_display
        self.walker = main_display.walker
        self.smart_home = smart_home

    def get_text(self):
        etext = self.get_edit_text()
        tokens = self.walker.get_tokens(self)
        attrib = [(tok, len(s)) for tok, s in tokens]
        return etext, attrib

    def insert_text(self, text):
        self.walker.all_tokens = None
        super().insert_text(text)

    def keypress(self, size, key):
        orig_pos = self.edit_pos
        orig_allow_tab, self.allow_tab = self.allow_tab, False
        rtn = super().keypress(size, key)
        self.allow_tab = orig_allow_tab
        if key == "left" or key == "right":
            self.main_display.reset_status()
        elif key == "backspace" or key == "delete":
            self.walker.all_tokens = None
        elif self.smart_home and key == "home":
            m = RE_NOT_SPACE.search(self.edit_text or "")
            i = 0 if m is None else m.start()
            i = 0 if i == orig_pos else i
            self.set_edit_pos(i)
            self.main_display.reset_status()
        elif orig_allow_tab and key == "tab":
            key = " "*(self.tabsize - (self.edit_pos%self.tabsize))
            self.insert_text(key)
        return rtn

class GotoEditor(urwid.Edit):
    """Editor to trigger jumps."""
    def run(self, main_display):
        m = RE_TWO_DIGITS.search(self.get_edit_text())
        if m is None:
            return "error!  "
        line, _, col = m.groups()
        main_display.walker.goto(int(line), int(col or 1))

class DequeEditor(urwid.Edit):
    """An editor that uses values from a deque or list.  Useful for histories."""
    def __init__(self, deq=None, **kwargs):
        super().__init__(**kwargs)
        self.deq = deq
        self.i = self.max_i = len(deq)  # index
        self.orig_text = ""

    def text_at(self, i):
        return self.deq[i]

    def keypress(self, size, key):
        rtn = super().keypress(size, key)
        if key == "up":
            i = self.i
            if i == self.max_i:
                self.orig_text = self.edit_text
            i = i - 1 if i > 0 else 0
            if len(self.deq) > 0:
                self.set_edit_text(self.text_at(i))
            self.i = i
        elif key == "down":
            i = self.i
            i = i + 1 if i < self.max_i else i
            if i == self.max_i:
                self.set_edit_text(self.orig_text)
            else:
                self.set_edit_text(self.text_at(i))
            self.i = i
        return rtn

class QueryEditor(DequeEditor):
    """Sets a (compiled) regular expression on the main body."""
    def run(self, main_display):
        try:
            q = re.compile(self.get_edit_text())
        except re.error:
            return "re fail "
        main_display.queries.append(q)
        return main_display.seek_match()

    def text_at(self, i):
        return self.deq[i].pattern

class ReplacementEditor(DequeEditor):
    """Sets a replacement string on the main body."""
    def run(self, main_display):
        r = self.get_edit_text()
        main_display.replacements.append(r)
        return main_display.replace_match()

class StyleSelectorEditor(urwid.Edit):
    """Editor to select pygments style."""
    def run(self, main_display):
        try:
            s = get_style_by_name(self.edit_text.strip())
        except pygments.util.ClassNotFound:
            return "bad sty "
        main_display.register_palette(s)

class FileSelectorEditor(urwid.Edit):
    """Editor to select file from filesystem."""

    def filename(self):
        return os.path.expandvars(os.path.expanduser(self.edit_text.strip()))

    def run(self, main_display):
        fname = self.filename()
        if os.path.isdir(fname):
            return "is dir! "
        elif not os.path.exists(fname):
            return "no file "
        main_display.load_file(fname)

    def keypress(self, size, key):
        orig_pos = self.edit_pos
        rtn = super().keypress(size, key)
        if key == "tab":
            fname = self.filename()
            globbed = glob(fname + '*')
            common = os.path.commonprefix(globbed)
            if len(common) > 0:
                self.set_edit_text(common)
                self.set_edit_pos(len(common))
                common_globbed = glob(common + "*")
                if len(common_globbed) > 1:
                    cap = "{0}\nread in file: ".format(" ".join(common_globbed))
                    self.set_caption(cap)
                else:
                    self.set_caption("read in file: ")
        return rtn

class LineWalker(urwid.ListWalker):
    """ListWalker-compatible class for lazily reading file contents."""

    def __init__(self, name, main_display, tabsize, multiline_window=1500,
                 number_of_windows=1):
        self.name = name
        self.file = f = open(name)
        try:
            lexer = guess_lexer_for_filename(name, f.readline())
        except TypeError:
            try:
                lexer = get_lexer_by_name(os.path.splitext(name)[1][1:])
            except pygments.util.ClassNotFound:
                lexer = TextLexer()
        except pygments.util.ClassNotFound:
            lexer = TextLexer()
        lexer = Python3Lexer() if isinstance(lexer, PythonLexer) else lexer
        lexer.add_filter(NonEmptyFilter())
        lexer.add_filter('tokenmerge')
        f.seek(0)
        self.lines = []
        self.focus = 0
        self.clipboard = None
        self.clipboard_pos = None
        self.lexer = lexer
        self.w_pos = {}
        self.all_tokens = None
        self._etext = lambda w: w.edit_text
        self.multiline_window = multiline_window
        self.number_of_windows = number_of_windows
        self.main_display = main_display
        self.line_kwargs = dict(caption="", allow_tab=True, lexer=lexer,
                                wrap='clip', main_display=main_display,
                                smart_home=True, tabsize=tabsize)

    def get_pos(self, w):
        w_pos = self.w_pos
        lines = self.lines
        llen = len(lines)
        pos_guess = w_pos.get(w, llen//2)
        if pos_guess < llen and w is lines[pos_guess]:
            return pos_guess
        for uppos, dnpos in zip_longest(range(pos_guess+1, llen), range(pos_guess-1, -1, -1)):
            if uppos is not None and llen > uppos and w is lines[uppos]:
                w_pos[w] = uppos
                return uppos
            if dnpos is not None and llen > dnpos and w is lines[dnpos]:
                w_pos[w] = dnpos
                return dnpos

    def get_focus(self):
        return self._get_at_pos(self.focus)

    def set_focus(self, focus):
        self.focus = focus
        self._modified()
        self.main_display.reset_status()

    def get_next(self, start_from):
        return self._get_at_pos(start_from + 1)

    def get_prev(self, start_from):
        return self._get_at_pos(start_from - 1)

    def read_next_line(self):
        """Read another line from the file."""
        next_line = self.file.readline()
        if not next_line or next_line[-1:] != '\n':
            self.file = None  # no newline on last line of file
        else:
            next_line = next_line[:-1]  # trim newline characters
        edit = LineEditor(edit_text=next_line, **self.line_kwargs)
        edit.set_edit_pos(0)
        self.w_pos[edit] = len(self.lines)
        self.lines.append(edit)
        return next_line

    def _get_at_pos(self, pos):
        """Return a widget for the line number passed."""
        if pos < 0:
            return None, None  # line 0 is the start of the file, no more above
        if len(self.lines) > pos:
            return self.lines[pos], pos  # we have that line so return it
        if self.file is None:
            return None, None  # file is closed, so there are no more lines
        self._ensure_read_in(pos)
        return self.lines[-1], pos

    def _ensure_read_in(self, lineno):
        next_line = ""
        n = 0
        while lineno >= len(self.lines) and next_line is not None \
                                        and self.file is not None:
            next_line = self.read_next_line()
            n += 1
        if n >= 2:
            self.all_tokens = None

    def split_focus(self):
        """Divide the focus edit widget at the cursor location."""
        self.all_tokens = None
        focus = self.lines[self.focus]
        pos = focus.edit_pos
        edit = LineEditor(edit_text=focus.edit_text[pos:], **self.line_kwargs)
        edit.original_text = None
        focus.set_edit_text(focus.edit_text[:pos])
        edit.set_edit_pos(0)
        self.lines.insert(self.focus+1, edit)
        self.w_pos[edit] = self.focus

    def combine_focus_with_prev(self):
        """Combine the focus edit widget with the one above."""
        self.all_tokens = None
        above, ignore = self.get_prev(self.focus)
        if above is None:
            return  # already at the top
        focus = self.lines[self.focus]
        above.set_edit_pos(len(above.edit_text))
        above.set_edit_text(above.edit_text + focus.edit_text)
        del self.w_pos[self.lines[self.focus]]
        del self.lines[self.focus]
        self.focus -= 1

    def combine_focus_with_next(self):
        """Combine the focus edit widget with the one below."""
        self.all_tokens = None
        below, ignore = self.get_next(self.focus)
        if below is None:
            return  # already at bottom
        focus = self.lines[self.focus]
        focus.set_edit_text(focus.edit_text + below.edit_text)
        del self.w_pos[self.lines[self.focus+1]]
        del self.lines[self.focus+1]

    # Some nice functions
    def get_coords(self):
        """Returns the line & col position. These are 1-indexed."""
        focus = self.focus
        return focus + 1, (self.lines[focus].edit_pos or 0) + 1

    def goto(self, lineno, col):
        """Jumps to a specific line & column.  These are 1-indexed."""
        self._ensure_read_in(lineno)
        focus = min(lineno, len(self.lines)) - 1
        self.lines[focus].set_edit_pos(col - 1)
        self.set_focus(focus)

    def seek_match(self, q):
        """Finds the next match to the regular expression q and goes there."""
        m = None
        orig_pos = self.focus
        curr_pos = orig_pos - 1
        last_pos = curr_pos - 1
        while m is None and last_pos != curr_pos:
            # search down the lines
            last_pos = curr_pos
            w, curr_pos = self.get_next(curr_pos)
            if w is None:
                m = None
                break
            m = q.search(w.get_edit_text(), w.edit_pos+1 if curr_pos == orig_pos else 0)
        if m is None:
           curr_pos = 0  # start from the top
        while m is None and curr_pos < orig_pos:
            w, curr_pos = self.get_next(curr_pos)
            m = q.search(w.get_edit_text())
        if m is None:
            return "0 res.  "
        self.goto(curr_pos + 1, m.start() + 1)

    def replace_match(self, q, r):
        """Finds & replaces the next match to the regular expression q."""
        stat = self.seek_match(q)
        if stat is not None:
            return stat
        w, ypos = self.get_focus()
        xpos = w.edit_pos
        text = w.edit_text
        s = q.sub(r, text[xpos:], count=1)
        w.set_edit_text(text[:xpos] + s)
        w.set_edit_pos(xpos)

    # tokenization
    def _compute_slice(self, pos, window, alltokens):
        llen = len(self.lines)
        q = pos // window
        slc = slice(max((q*window)-3, 0), min(((q+1)*window)+3, llen))
        alltokens[slc] = self.get_all_tokens(lines=self.lines[slc])

    def get_tokens(self, w, window=None):
        """Computes the tokens for a widget, but first tries to look them up from
        a cache on the class.
        """
        alltokens = self.all_tokens
        pos = self.get_pos(w)
        window = window or self.multiline_window
        if len(self.lines) > window * self.number_of_windows:
            # Short circut windowing if we have too many lines.
            return self.get_basic_tokens(w)
        if alltokens is None:
            # this funny business with windowing makes typing responsive
            self.all_tokens = alltokens = [None] * len(self.lines)
            self._compute_slice(pos, window, alltokens)
        if pos >= len(alltokens):
            # for adding or removing lines
            return self.get_basic_tokens(w)
        wtoks = alltokens[pos]
        if wtoks is None:
            # for adding or remving line (last resort - suffocation, no breathing)
            alltokens[pos] = wtoks = self.get_basic_tokens(w)
        return wtoks

    def get_basic_tokens(self, w):
        return list(self.lexer.get_tokens(w.edit_text))

    def get_all_tokens(self, lines=None):
        lines = lines or self.lines
        viewtext = "\n".join(map(self._etext, lines))
        ltokens = []
        alltokens = []
        for token, s in self.lexer.get_tokens(viewtext):
            if len(s) == 0:
                continue
            if '\n' not in s:
                ltokens.append((token, s))
                continue
            spl = s.split('\n')
            ltokens.append((token, spl[0]))
            for text in spl[1:]:
                alltokens.append(ltokens)
                ltokens = [(token, text)]
        return alltokens

    # Clipboard methods
    def cut_to_clipboard(self):
        """Cuts the current line to the clipboard."""
        focus = self.focus
        if focus + 1 == len(self.lines):
           return  # don't cut last line
        self.all_tokens = None
        if (self.clipboard is None) or (self.clipboard_pos is None) or \
           (focus != self.clipboard_pos):
            self.clipboard = []
        w = self.lines.pop(focus)
        del self.w_pos[w]
        self.clipboard.append(w)
        self.clipboard_pos = focus
        self.set_focus(focus)

    def paste_from_clipboard(self):
        """Insert lines from the clipboard at the current position."""
        cb = self.clipboard
        if cb is None:
            return
        self.all_tokens = None
        for line in cb[::-1]:
            self.all_tokens = None
            newline = LineEditor(edit_text=line.get_edit_text(), **self.line_kwargs)
            newline.original_text = None
            self.lines.insert(self.focus, newline)
            self.w_pos[newline] = self.focus
        self.all_tokens = None
        self.set_focus(self.focus + len(cb))

    def clear_clipboard(self):
        """Removes the existing clipboard, destroying all lines in the process."""
        self.clipboard = self.clipboard_pos = None

    def insert_raw_lines(self, rawlines):
        """Inserts strings at the current position."""
        pos = self.focus
        rawlines.reverse()
        self.all_tokens = None
        for rawline in rawlines:
            self.all_tokens = None
            newline = LineEditor(edit_text=rawline, **self.line_kwargs)
            self.lines.insert(pos, newline)
            self.w_pos[newline] = pos
        self.all_tokens = None
        rawlines.reverse()

class MainDisplay(object):
    base_palette = [('body', 'default', 'default'),
                    ('foot', 'black', 'dark blue', 'bold'),
                    ('key', 'black', 'dark magenta', 'underline'),]

    status_text = ('foot', ["xo    ", ('key', "^x"), " exit ",
                                      ('key', "^o"), " save ",
                                      ('key', "esc"), " help ", ""])

    def __init__(self):
        self.load_rc()
        self.set_keybindings()

    def init_file(self, name):
        self.save_name = name
        self.set_tabs()
        self.walker = LineWalker(name, main_display=self, tabsize=self.tabsize,
                                 multiline_window=self.rc['multiline_window'])
        self.listbox = urwid.ListBox(self.walker)
        self.status = urwid.AttrMap(urwid.Text(self.status_text), "foot")
        self.view = urwid.Frame(urwid.AttrMap(self.listbox, 'body'),
                                footer=self.status)
        self.clipboard = None
        self.queries = deque(self.rc["queries"], maxlen=self.rc["max_queries"])
        self.replacements = deque(self.rc["replacements"],
                                  maxlen=self.rc["max_replacements"])

    def load_rc(self):
        cacherc = json_rc_load('~/.cache/xo/rc.json')
        configrc = json_rc_load(RC_PATH)
        rc = merge_rcs(DEFAULT_RC, cacherc)
        rc = merge_rcs(rc, configrc)
        rc["queries"] = [re.compile(q) for q in rc["queries"]]
        self.rc = rc

    def dump_cache(self):
        cacherc = {"replacements": list(self.replacements),
                   "queries": [q.pattern for q in self.queries]}
        dname = os.path.expanduser('~/.cache/xo/')
        if not os.path.isdir(dname):
            os.makedirs(dname)
        fname = os.path.join(dname, 'rc.json')
        with open(fname, 'w') as f:
            json.dump(cacherc, f)

    def set_tabs(self):
        name = self.save_name
        for tab in sorted(self.rc["tabs"].items(), reverse=True):
            # reverse ensures longest match
            if name.endswith(tab[0]):
                self.tabsize, self.must_retab = tab[1]
                break
        else:
            self.tabsize, self.must_retab = self.rc["tabs"]["default"]

    def set_keybindings(self):
        self.keybindings = self.rc["keybindings"]
        exit_text = '-'.join(self.keybindings['exit'].split())
        exit_text = exit_text.replace('ctrl-', '^')
        self.status_text[1][1] = ('key', exit_text)
        save_text = '-'.join(self.keybindings['save'].split())
        save_text = save_text.replace('ctrl-', '^')
        self.status_text[1][3] = ('key', save_text)

    def register_palette(self, style_class):
        """Converts pygmets style to urwid palatte"""
        default = 'default'
        palette = list(self.base_palette)
        mapping = self.rc['rgb_to_short']
        for tok in style_class.styles.keys():
            for t in tok.split()[::-1]:
                st = style_class.styles[t]
                if '#' in st:
                    break
            if '#' not in st:
                st = ''
            st = st.split()
            st.sort()   # '#' comes before '[A-Za-z0-9]'
            if len(st) == 0:
                c = default
            elif st[0].startswith('bg:'):
                c = default
            elif len(st[0]) == 7:
                c = 'h' + rgb_to_short(st[0][1:], mapping)[0]
            elif len(st[0]) == 4:
                c = 'h' + rgb_to_short(st[0][1]*2 + st[0][2]*2 + st[0][3]*2, mapping)[0]
            else:
                c = default
            a = urwid.AttrSpec(c, default, colors=256)
            row = (tok, default, default, default, a.foreground, default)
            palette.append(row)
        self.loop.screen.register_palette(palette)

    def main(self, line=1, col=1):
        loop = urwid.MainLoop(self.view,
            handle_mouse=False,
            unhandled_input=self.unhandled_keypress)
        loop.screen.set_terminal_properties(256)
        self.loop = loop
        self.register_palette(get_style_by_name(self.rc["style"]))
        self.walker.goto(line, col)
        self.walker.all_tokens = None
        while True:
            try:
                self.loop.run()
            except KeyboardInterrupt:
                self.reset_status(status="YOLO!   ")
            else:
                break

    def seek_match(self):
        """Finds and jumps to the next match for the current query."""
        if len(self.queries) == 0:
            stat = "no re   "
        else:
            stat = self.walker.seek_match(self.queries[-1])
        return stat

    def replace_match(self):
        """Finds, jumps, and substitues to the next match for the current query &
        replacement.
        """
        if len(self.queries) == 0:
            stat = "no re   "
        elif len(self.replacements) == 0:
            stat = "no sub  "
        else:
            stat = self.walker.replace_match(self.queries[-1], self.replacements[-1])
        return stat

    def load_file(self, fname):
        with open(fname) as f:
             rawlines = f.readlines()
        self.walker.insert_raw_lines(rawlines)

    def reset_status(self, status="xo      ", *args, **kwargs):
        ncol, nrow = self.loop.screen.get_cols_rows()
        ft = self.status_text
        ft[1][0] = status
        flc = "{0}:{1[0]}:{1[1]}".format(self.save_name, self.walker.get_coords())
        ft[1][-1] = "{0: >{1}}".format(flc, max(ncol - 33, 0))
        self.status.original_widget.set_text(ft)

    def unhandled_keypress(self, k):
        """Where the main app handles keypresses."""
        status = "xo      "
        fp = self.view.focus_position
        keybindings = self.keybindings
        if k == keybindings["save"]:
            self.save_file()
            status = "saved   "
        elif k == keybindings["exit"]:
            self.dump_cache()
            raise urwid.ExitMainLoop()
        elif k == "delete" and fp == "body":
            # delete at end of line
            self.walker.combine_focus_with_next()
        elif k == "backspace" and fp == "body":
            # backspace at beginning of line
            self.walker.combine_focus_with_prev()
        elif k == "enter":
            if fp == "body":
                self.walker.split_focus()  # start new line
                self.loop.process_input(["down", "home"])
            elif fp == "footer":
                w = self.view.focus.original_widget
                if hasattr(w, "run"):
                    status = w.run(self) or status
                self.view.focus_position = "body"
                self.view.contents["footer"] = (self.status, None)
        elif k == "right":
            w, pos = self.walker.get_focus()
            w, pos = self.walker.get_next(pos)
            if w:
                self.listbox.set_focus(pos, 'above')
                self.loop.process_input(["home"])
        elif k == "left":
            w, pos = self.walker.get_focus()
            w, pos = self.walker.get_prev(pos)
            if w:
                self.listbox.set_focus(pos, 'below')
                self.loop.process_input(["end"])
        elif k == keybindings["cut"]:
            self.walker.cut_to_clipboard()
            status = "cut     "
        elif k == keybindings["paste"]:
            self.walker.paste_from_clipboard()
            status = "pasted  "
        elif k == keybindings["clear_clipboard"]:
            self.walker.clear_clipboard()
            status = "cleared "
        elif k == "ctrl left" or k == "meta left":
            w, ypos = self.walker.get_focus()
            xpos = w.edit_pos
            re_word = RE_WORD if k == "ctrl left" else RE_NOT_WORD
            starts = [m.start() for m in re_word.finditer(w.edit_text or "", 0, xpos)]
            word_pos = xpos if len(starts) == 0 else starts[-1]
            w.set_edit_pos(word_pos)
        elif k == "ctrl right" or k == "meta right":
            w, ypos = self.walker.get_focus()
            xpos = w.edit_pos
            re_word = RE_WORD if k == "meta right" else RE_NOT_WORD
            m = re_word.search(w.edit_text or "", xpos)
            word_pos = xpos if m is None else m.end()
            w.set_edit_pos(word_pos)
        elif k == keybindings["jump"]:
            curr_footer = self.view.contents["footer"][0]
            if curr_footer is self.status:
                self.view.contents["footer"] = (
                    urwid.AttrMap(GotoEditor("line & col: ", ""), "foot"), None)
                self.view.focus_position = "footer"
        elif k == keybindings["find"]:
            curr_footer = self.view.contents["footer"][0]
            if curr_footer is self.status:
                self.view.contents["footer"] = (
                    urwid.AttrMap(QueryEditor(caption="re: ", edit_text="",
                                  deq=self.queries), "foot"), None)
                self.view.focus_position = "footer"
        elif k == keybindings["find_next"]:
            status = self.seek_match() or status
        elif k == keybindings["replace"]:
            curr_footer = self.view.contents["footer"][0]
            w = curr_footer.original_widget
            if isinstance(w, QueryEditor):
                status = w.run(self) or status
                self.view.focus_position = "body"
                self.view.contents["footer"] = (self.status, None)
                curr_footer = self.status
            if curr_footer is self.status:
                self.view.contents["footer"] = (
                    urwid.AttrMap(ReplacementEditor(caption="sub: ", edit_text="",
                                  deq=self.replacements), "foot"), None)
                self.view.focus_position = "footer"
        elif k == keybindings["replace_next"]:
            w = self.view.contents["footer"][0].original_widget
            if isinstance(w, QueryEditor):
                status = w.run(self) or status
                self.view.focus_position = "body"
                self.view.contents["footer"] = (self.status, None)
            status = self.replace_match() or status
        elif k == keybindings["style"]:
            curr_footer = self.view.contents["footer"][0]
            if curr_footer is self.status:
                cap = "available styles: {0}\nchoose one: "
                cap = cap.format(" ".join(sorted(get_all_styles())))
                self.view.contents["footer"] = (urwid.AttrMap(StyleSelectorEditor(
                    caption=cap, edit_text=""), "foot"), None)
                self.view.focus_position = "footer"
        elif k == keybindings["insert"]:
            curr_footer = self.view.contents["footer"][0]
            if curr_footer is self.status:
                self.view.contents["footer"] = (urwid.AttrMap(FileSelectorEditor(
                    caption="read in file: ", edit_text=""), "foot"), None)
                self.view.focus_position = "footer"
        elif k == "esc":
            curr_footer = self.view.contents["footer"][0]
            if curr_footer is self.status:
                self.view.contents["footer"] = (
                    urwid.AttrMap(urwid.Text(__doc__.format(**self.keybindings)),
                    "foot"), None)
                self.view.focus_position = "footer"
            else:
                self.view.contents["footer"] = (self.status, None)
                self.view.focus_position = "body"
        else:
            self.reset_status()
            return
        self.reset_status(status=status)
        return True

    def save_file(self):
        """Write the file out to disk."""
        newlines = []
        tabsize = self.tabsize
        must_retab = self.must_retab
        walker = self.walker
        for line in walker.lines:
            # collect the text already stored in edit widgets
            edit_text = line.edit_text
            orig_text = line.original_text
            if orig_text is None:
                newline = retab(edit_text, tabsize) if must_retab else edit_text
            elif sanitize_text(orig_text, tabsize) == edit_text:
                newline = orig_text
            else:
                newline = retab(edit_text, tabsize) if must_retab else edit_text
            newlines.append(ensure_endswith_newline(newline))

        while walker.file is not None:  # grab remaining lines
            newlines.append(ensure_endswith_newline(walker.read_next_line()))
        newlines = [line.rstrip() + '\n' for line in newlines]

        last_line = newlines[-1]
        newlines[-1] = last_line[:-1] if last_line.endswith('\n') else last_line
        with open(self.save_name, "w") as f:
            for newline in newlines:
                f.write(newline)

ensure_endswith_newline = lambda x: x if x.endswith('\n') else x + '\n'

def retab(s, tabsize):
    # via http://code.activestate.com/recipes/65226-expanding-and-compressing-tabs/
    pieces = RE_SPACES.split(s)
    for i, piece in enumerate(pieces):
        thislen = len(piece)
        if piece.isspace():
            numtabs = thislen // tabsize
            numblanks = thislen % tabsize
            pieces[i] = '\t' * numtabs + ' ' * numblanks
    return ''.join(pieces)

def touch(filename):
    """Opens a file and updates the mtime, like the posix command of the same name."""
    with io.open(filename, 'a') as f:
        os.utime(filename, None)

def path_line_col(x):
    x = x.rstrip(':')
    plc = x.rsplit(':', 2)
    plc += [1] * (3 - len(plc))
    return plc[0], int(plc[1] or 1), int(plc[2] or 1)

def main(args=None):
    main_display = MainDisplay()
    parser = ArgumentParser(prog='xo', formatter_class=RawDescriptionHelpFormatter,
                            description=__doc__.format(**main_display.keybindings))
    parser.add_argument('path',
                        help=("path to file, may include colon separated "
                              "line and col numbers, eg 'path/to/xo.py:10:42'"))
    parser.add_argument('--rc', default=False, action="store_true",
                        help="display run control file")
    parser.add_argument('--rc-edit', default=False, action="store_true",
                        help="open run control file")
    ns = parser.parse_args(args=args)
    if ns.rc:
        with open(RC_PATH) as f:
            print(f.read())
        sys.exit()
    ns.path = RC_PATH if ns.rc_edit else ns.path
    path, line, col = path_line_col(ns.path)
    if not os.path.exists(path):
        touch(path)
    elif os.path.isdir(path):
        sys.exit("Error: may not open directory {0!r}".format(path))
    main_display.init_file(path)
    main_display.main(line, col)

if __name__=="__main__":
    main()
