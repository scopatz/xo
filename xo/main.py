#!/usr/bin/env python3
"""exofrills: your text has been edited...but you are still hungry.

key commands
------------
esc: get help
ctrl + o: save file (write-out)
ctrl + x: exit (does not save)

meta + s: select pygments style
ctrl + f: insert file at current position
ctrl + y: go to line & column (yalla, let's bounce)

ctrl + k: cuts the current line to the clipboard
ctrl + u: pastes the clipboard to the current line
ctrl + t: clears the clipboard (these spell K-U-T)

ctrl + w: set regular expression and jump to first match
meta + w: jump to next match of current regular expression
ctrl + r: set substitution for regular expression and replace first match
meta + r: replace next match of current regular expression
"""
import os
import re
import io
import sys
from glob import glob
from collections import deque
from argparse import ArgumentParser, RawDescriptionHelpFormatter

import urwid
import pygments.util
from pygments.lexers import guess_lexer, guess_lexer_for_filename, get_lexer_by_name
from pygments.lexers.special import TextLexer
from pygments.filter import Filter
from pygments.styles import get_all_styles, get_style_by_name

from colortrans import rgb2short

RE_WORD = re.compile(r'\w+')
RE_NOT_WORD = re.compile(r'\W+')
RE_NOT_SPACE = re.compile(r'\S')
RE_TWO_DIGITS = re.compile("(\d+)(\D+)?(\d+)?")
RE_SPACES = re.compile(r'( +)')

DEFAULT_RC = {
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
    }

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
        self.smart_home = smart_home

    def get_text(self):
        etext = self.get_edit_text()
        tokens = self.lexer.get_tokens(etext)
        attrib = [(tok, len(s)) for tok, s in tokens]
        return etext, attrib

    def keypress(self, size, key):
        orig_pos = self.edit_pos
        orig_allow_tab, self.allow_tab = self.allow_tab, False
        rtn = super().keypress(size, key)
        self.allow_tab = orig_allow_tab
        if key == "left" or key == "right":
            self.main_display.reset_status()
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
    
    def __init__(self, name, main_display, tabsize):
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
        lexer.add_filter(NonEmptyFilter())
        lexer.add_filter('tokenmerge')
        f.seek(0)
        self.lines = []
        self.focus = 0
        self.clipboard = None
        self.clipboard_pos = None
        self.lexer = lexer
        self.main_display = main_display
        self.line_kwargs = dict(caption="", allow_tab=True, lexer=lexer, 
                                wrap='clip', main_display=main_display, 
                                smart_home=True, tabsize=tabsize)
   
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
        self.lines.append(edit)
        return next_line
    
    def _get_at_pos(self, pos):
        """Return a widget for the line number passed."""
        
        if pos < 0:
            # line 0 is the start of the file, no more above
            return None, None
            
        if len(self.lines) > pos:
            # we have that line so return it
            return self.lines[pos], pos

        if self.file is None:
            return None, None  # file is closed, so there are no more lines
        self._ensure_read_in(pos)
        return self.lines[-1], pos

    def _ensure_read_in(self, lineno):
        next_line = ""
        while lineno >= len(self.lines) and next_line is not None \
                                        and self.file is not None:
            next_line = self.read_next_line()
    
    def split_focus(self):
        """Divide the focus edit widget at the cursor location."""
        focus = self.lines[self.focus]
        pos = focus.edit_pos
        edit = LineEditor(edit_text=focus.edit_text[pos:], **self.line_kwargs)
        edit.original_text = None
        focus.set_edit_text(focus.edit_text[:pos])
        edit.set_edit_pos(0)
        self.lines.insert(self.focus+1, edit)

    def combine_focus_with_prev(self):
        """Combine the focus edit widget with the one above."""
        above, ignore = self.get_prev(self.focus)
        if above is None:
            return  # already at the top
        focus = self.lines[self.focus]
        above.set_edit_pos(len(above.edit_text))
        above.set_edit_text(above.edit_text + focus.edit_text)
        del self.lines[self.focus]
        self.focus -= 1

    def combine_focus_with_next(self):
        """Combine the focus edit widget with the one below."""
        below, ignore = self.get_next(self.focus)
        if below is None:
            return  # already at bottom
        focus = self.lines[self.focus]
        focus.set_edit_text(focus.edit_text + below.edit_text)
        del self.lines[self.focus+1]

    #
    # Some nice functions
    #
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

    #
    # Clipboard methods
    #
    def cut_to_clipboard(self):
        """Cuts the current line to the clipboard."""
        focus = self.focus
        if focus + 1 == len(self.lines):
           return  # don't cut last line
        if (self.clipboard is None) or (self.clipboard_pos is None) or \
           (focus != self.clipboard_pos):
            self.clipboard = []
        self.clipboard.append(self.lines.pop(focus))
        self.clipboard_pos = focus
        self.set_focus(focus)

    def paste_from_clipboard(self):
        """Insert lines from the clipboard at the current position."""
        cb = self.clipboard
        if cb is None:
            return
        for line in cb[::-1]:
            newline = LineEditor(edit_text=line.get_edit_text(), **self.line_kwargs)
            newline.original_text = None
            self.lines.insert(self.focus, newline)
        self.set_focus(self.focus + len(cb))

    def clear_clipboard(self):
        """Removes the existing clipboard, destroying all lines in the process."""
        self.clipboard = self.clipboard_pos = None

    def insert_raw_lines(self, rawlines):
        """Inserts strings at the current position."""
        pos = self.focus
        rawlines.reverse()
        for rawline in rawlines:
            newline = LineEditor(edit_text=rawline, **self.line_kwargs)
            self.lines.insert(pos, newline)
        rawlines.reverse()

class MainDisplay(object):
    base_palette = [
        ('body', 'default', 'default'),
        ('foot', 'black', 'dark blue', 'bold'),
        ('key', 'black', 'dark magenta', 'underline'),
        ]
        
    status_text = ('foot', [
        "xo    ",
        ('key', "^x"), " exit ",
        ('key', "^o"), " save ",
        ('key', "esc"), " help ",
        ""
        ])
    
    def __init__(self, name):
        self.save_name = name
        self.rc = DEFAULT_RC
        self.set_tabs()
        self.walker = LineWalker(name, main_display=self, tabsize=self.tabsize)
        self.listbox = urwid.ListBox(self.walker)
        self.status = urwid.AttrMap(urwid.Text(self.status_text), "foot")
        self.view = urwid.Frame(urwid.AttrMap(self.listbox, 'body'),
                                footer=self.status)
        self.clipboard = None
        self.queries = deque(maxlen=128)
        self.replacements = deque(maxlen=128)

    def set_tabs(self):
        name = self.save_name
        for tab in sorted(self.rc["tabs"].items(), reverse=True):
            # reverse ensures longest match 
            if name.endswith(tab[0]):
                self.tabsize, self.must_retab = tab[1]
                break
        else:
            self.tabsize, self.must_retab = self.rc["tabs"]["default"]

    def register_palette(self, style_class):
        """Converts pygmets style to urwid palatte"""
        default = 'default'
        palette = list(self.base_palette)
        for tok, st in style_class.styles.items():
            if '#' not in st:
                st = ''
            st = st.split()
            st.sort()   # '#' comes before '[A-Za-z0-9]'
            if len(st) == 0: 
                c = default 
            elif st[0].startswith('bg:'):
                c = default
            elif len(st[0]) == 7:
                c = 'h' + rgb2short(st[0][1:])[0]
            elif len(st[0]) == 4:
                c = 'h' + rgb2short(st[0][1]*2 + st[0][2]*2 + st[0][3]*2)[0]
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
        self.loop.run()

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
        if k == "ctrl o":
            self.save_file()
            status = "saved   "
        elif k == "ctrl x":
            raise urwid.ExitMainLoop()
        elif k == "delete":
            # delete at end of line
            self.walker.combine_focus_with_next()
        elif k == "backspace":
            # backspace at beginning of line
            self.walker.combine_focus_with_prev()
        elif k == "enter":
            fp = self.view.focus_position
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
        elif k == "ctrl k":
            self.walker.cut_to_clipboard()
            status = "cut     "
        elif k == "ctrl u":
            self.walker.paste_from_clipboard()
            status = "pasted  "
        elif k == "ctrl t":
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
        elif k == "ctrl y":
            curr_footer = self.view.contents["footer"][0]
            if curr_footer is self.status:
                self.view.contents["footer"] = (
                    urwid.AttrMap(GotoEditor("line & col: ", ""), "foot"), None)
                self.view.focus_position = "footer"
        elif k == "ctrl w":
            curr_footer = self.view.contents["footer"][0]
            if curr_footer is self.status:
                self.view.contents["footer"] = (
                    urwid.AttrMap(QueryEditor(caption="re: ", edit_text="", 
                                  deq=self.queries), "foot"), None)
                self.view.focus_position = "footer"
        elif k == "meta w":
            status = self.seek_match() or status
        elif k == "ctrl r":
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
        elif k == "meta r":
            w = self.view.contents["footer"][0].original_widget
            if isinstance(w, QueryEditor):
                status = w.run(self) or status
                self.view.focus_position = "body"
                self.view.contents["footer"] = (self.status, None)
            status = self.replace_match() or status
        elif k == "meta s":
            curr_footer = self.view.contents["footer"][0]
            if curr_footer is self.status:
                cap = "available styles: {0}\nchoose one: "
                cap = cap.format(" ".join(sorted(get_all_styles())))
                self.view.contents["footer"] = (urwid.AttrMap(StyleSelectorEditor(
                    caption=cap, edit_text=""), "foot"), None)
                self.view.focus_position = "footer"
        elif k == "ctrl f":
            curr_footer = self.view.contents["footer"][0]
            if curr_footer is self.status:
                self.view.contents["footer"] = (urwid.AttrMap(FileSelectorEditor(
                    caption="read in file: ", edit_text=""), "foot"), None)
                self.view.focus_position = "footer"
        elif k == "esc":
            curr_footer = self.view.contents["footer"][0]
            if curr_footer is self.status:
                self.view.contents["footer"] = (
                    urwid.AttrMap(urwid.Text(__doc__.strip()), "foot"), None)
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
            numtabs = thislen / tabsize
            numblanks = thislen % tabsize
            pieces[i] = '\t' * numtabs + ' ' * numblanks
    return ''.join(pieces)

def touch(filename):
    """Opens a file and updates the mtime, like the posix command of the same name."""
    with io.open(filename, 'a') as f:
        os.utime(filename, None)

def path_line_col(x):
    plc = x.rsplit(':', 2)
    plc += [1] * (3 - len(plc))
    return plc[0], int(plc[1] or 1), int(plc[2] or 1)

def main():
    parser = ArgumentParser(prog='xo', description=__doc__, 
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('path', help=("path to file, may include colon separated "
                                      "line and col numbers, eg 'path/to/xo.py:10:42'"))
    ns = parser.parse_args()
    path, line, col = path_line_col(ns.path)
    if not os.path.exists(path):
        touch(path)
    elif os.path.isdir(path):
        sys.exit("Error: may not open directory {0!r}".format(path))
    main_display = MainDisplay(path)
    main_display.main(line, col)

if __name__=="__main__": 
    main()
