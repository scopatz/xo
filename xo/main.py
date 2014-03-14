#!/usr/bin/env python3
"""exofrills: your text has been edited...but you are still hungry.

key commands
------------
esc: get help
ctrl + o: save file (write-out)
ctrl + x: exit (does not save)
meta + s: select pygments style

ctrl + k: cuts the current line to the clipboard
ctrl + u: pastes the clipboard to the current line
ctrl + t: clears the clipboard (these spell K-U-T)

ctrl + w: set regular expression and jump to first match
meta + w: jump to next match of current regular expression
ctrl + y: go to line & column (yalla, let's bounce)
"""
import os
import re
import io
import sys
from collections import deque
from argparse import ArgumentParser, RawDescriptionHelpFormatter

import urwid
import pygments.util
from pygments.lexers import guess_lexer, guess_lexer_for_filename, get_lexer_by_name
from pygments.lexers.special import TextLexer
from pygments.filter import Filter
from pygments.styles import get_all_styles, get_style_by_name
from pygments.styles.monokai import MonokaiStyle as S

from colortrans import rgb2short

RE_WORD = re.compile(r'\w+')
RE_NOT_WORD = re.compile(r'\W+')
RE_NOT_SPACE = re.compile(r'\S')
RE_TWO_DIGITS = re.compile("(\d+)(\D+)?(\d+)?")

class NonEmptyFilter(Filter):
    """Ensures that tokens have len > 0."""
    def filter(self, lexer, stream):
        for ttype, value in stream:
            if len(value) > 0:
                yield ttype, value

class LineEditor(urwid.Edit):

    def __init__(self, lexer=None, main_display=None, smart_home=True, **kwargs):
        super().__init__(**kwargs)
        if lexer is None:
           lexer = guess_lexer(self.get_edit_text())
        self.lexer = lexer
        self.main_display = main_display
        self.smart_home = smart_home

    def get_text(self):
        etext = self.get_edit_text()
        tokens = self.lexer.get_tokens(etext)
        attrib = [(tok, len(s)) for tok, s in tokens]
        return etext, attrib

    def keypress(self, size, key):
        orig_pos = self.edit_pos
        rtn = super().keypress(size, key)
        if key == "left" or key == "right":
            self.main_display.reset_status()
        elif self.smart_home and key == "home":
            m = RE_NOT_SPACE.search(self.edit_text or "")
            i = 0 if m is None else m.start()
            i = 0 if i == orig_pos else i
            self.set_edit_pos(i)
            self.main_display.reset_status()
        return rtn

class GotoEditor(urwid.Edit):
    """Editor to trigger jumps."""
    def run(self, main_display):
        m = RE_TWO_DIGITS.search(self.get_edit_text())
        if m is None:
            return "error!  "
        line, _, col = m.groups()
        main_display.walker.goto(int(line), int(col or 1))

class QueryEditor(urwid.Edit):
    """Sets a (compiled) regular expression on the main body."""
    def __init__(self, main_display=None, **kwargs):
        super().__init__(**kwargs)
        self.main_display = main_display
        self.qi = self.max_qi = len(main_display.queries)  # queries index
        self.orig_text = ""

    def run(self, main_display):
        try:
            q = re.compile(self.get_edit_text())
        except re.error:
            return "re fail "
        main_display.queries.append(q)
        return main_display.seek_match()

    def keypress(self, size, key):
        rtn = super().keypress(size, key)
        if key == "up":
            qi = self.qi
            if qi == self.max_qi:
                self.orig_text = self.edit_text
            qi = qi - 1 if qi > 0 else 0
            if len(self.main_display.queries) > 0:
                self.set_edit_text(self.main_display.queries[qi].pattern)
            self.qi = qi
        elif key == "down":
            qi = self.qi
            qi = qi + 1 if qi < self.max_qi else qi
            if qi == self.max_qi:
                self.set_edit_text(self.orig_text)
            else:
                self.set_edit_text(self.main_display.queries[qi].pattern)
            self.qi = qi
        return rtn

class StyleSelectorEditor(urwid.Edit):
    """Editor to select pygments style."""
    def run(self, main_display):
        try:
            s = get_style_by_name(self.edit_text.strip())
        except pygments.util.ClassNotFound:
            return "bad sty "
        main_display.register_palette(s)

class LineWalker(urwid.ListWalker):
    """ListWalker-compatible class for lazily reading file contents."""
    
    def __init__(self, name, main_display):
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
                                wrap='clip', main_display=main_display, smart_home=True)
   
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
            # no newline on last line of file
            self.file = None
        else:
            # trim newline characters
            next_line = next_line[:-1]

        expanded = next_line.expandtabs()
        
        edit = LineEditor(edit_text=expanded, **self.line_kwargs)
        edit.set_edit_pos(0)
        edit.original_text = next_line
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
        edit.original_text = ""
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
            newline.original_text = ""
            self.lines.insert(self.focus, newline)
        self.set_focus(self.focus + len(cb))

    def clear_clipboard(self):
        """Removes the existing clipboard, destroying all lines in the process."""
        self.clipboard = self.clipboard_pos = None

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
        self.walker = LineWalker(name, main_display=self) 
        self.listbox = urwid.ListBox(self.walker)
        self.status = urwid.AttrMap(urwid.Text(self.status_text), "foot")
        self.view = urwid.Frame(urwid.AttrMap(self.listbox, 'body'),
                                footer=self.status)
        self.clipboard = None
        self.queries = deque(maxlen=128)

    def register_palette(self, style_class):
        default = 'default'
        palette = list(self.base_palette)
        for tok, st in style_class.styles.items():
            if '#' not in st:
                st = ''
            st = st.split()
            st.sort()
            c = default if len(st) == 0 else 'h' + rgb2short(st[0][1:])[0]
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
        self.register_palette(get_style_by_name("monokai"))
        self.walker.goto(line, col)
        self.loop.run()

    def seek_match(self):
        """Finds and jumps to the next match for the current query."""
        if len(self.queries) == 0:
            stat = "no re   "
        else:
            stat = self.walker.seek_match(self.queries[-1])
        return stat

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
                    urwid.AttrMap(QueryEditor(caption="re: ", edit_text="", main_display=self), "foot"), None)
                self.view.focus_position = "footer"
        elif k == "meta w":
            status = self.seek_match() or status
        elif k == "meta s":
            curr_footer = self.view.contents["footer"][0]
            if curr_footer is self.status:
                cap = "available styles: {0}\nchoose one: "
                cap = cap.format(" ".join(sorted(get_all_styles())))
                self.view.contents["footer"] = (urwid.AttrMap(StyleSelectorEditor(
                    caption=cap, edit_text=""), "foot"), None)
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
        
        l = []
        walk = self.walker
        for edit in walk.lines:
            # collect the text already stored in edit widgets
            if edit.original_text.expandtabs() == edit.edit_text:
                l.append(edit.original_text)
            else:
                l.append(edit.edit_text)
        
        # then the rest
        while walk.file is not None:
            l.append(walk.read_next_line())
            
        # write back to disk
        outfile = open(self.save_name, "w")
        
        prefix = ""
        for line in l:
            outfile.write(prefix + line)
            prefix = "\n"

def re_tab(s):
    """Return a tabbed string from an expanded one."""
    l = []
    p = 0
    for i in range(8, len(s), 8):
        if s[i-2:i] == "  ":
            # collapse two or more spaces into a tab
            l.append(s[p:i].rstrip() + "\t")
            p = i

    if p == 0:
        return s
    else:
        l.append(s[p:])
        return "".join(l)

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
