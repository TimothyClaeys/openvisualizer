import curses
import curses.panel
import curses.textpad
import locale
import logging

from panel import Panel, PanelContainer

locale.setlocale(locale.LC_ALL, '')

code = locale.getpreferredencoding()

log = logging.getLogger("CmdPanel")


class CmdPanelContainer(PanelContainer):
    TITLE = " Command Interpreter "

    def __init__(self, render_lock, rows, cols, y, x):
        super(CmdPanelContainer, self).__init__(render_lock, rows, cols, y, x)

    def render_container(self):
        self.c_win.clear()
        self.c_win.border()
        self.c_win.addstr(0, int(self.cols / 2) - int(len(self.TITLE) / 2), self.TITLE, curses.A_STANDOUT)
        self.c_win.noutrefresh()

        for key in self.panels:
            self.panels[key].render_panel()

        with self.render_lock:
            curses.doupdate()

    def dispatch_click(self, y, x):
        pass

    def add_panel(self, panel_name=None, panel_id=0):
        cp = CmdPanel(self.render_lock, self.rows - 2, self.cols - 2, self.y + 1, self.x + 1)
        self.panels[panel_id] = cp


class ThreadSafeTextBox(curses.textpad.Textbox):
    def __init__(self, win, render_lock, insert=False):
        # use old-style super call, since Textbox is an old style class
        curses.textpad.Textbox.__init__(self, win, insert)
        self.render_lock = render_lock

    def edit(self, validate=None):
        while 1:
            ch = self.win.getch()
            if validate:
                ch = validate(ch)
            if not ch:
                continue
            if not self.do_command(ch):
                break

            with self.render_lock:
                self.win.refresh()

        return self.gather()


class CmdRepl(Panel):
    def __init__(self, render_lock, rows, cols, y, x):
        super(CmdRepl, self).__init__(render_lock, rows, cols, y, x)
        self.win.nodelay(False)

    def dispatch_click(self, y, x):
        pass

    def render_panel(self):
        self.win.clear()
        self.win.noutrefresh()


class CmdPanel(Panel):
    PROMPT = u'\u25b8'.encode(code)

    def __init__(self, render_lock, rows, cols, y, x):
        super(CmdPanel, self).__init__(render_lock, rows, cols, y, x)
        self.win.leaveok(True)

        self.repl = CmdRepl(render_lock, 1, self.cols - 4, self.y, self.x + 3)
        self.text_box = ThreadSafeTextBox(self.repl.win, render_lock)

    def mv_and_resize(self, rows, cols, y, x):
        super(CmdPanel, self).mv_and_resize(rows - 2, cols - 2, y + 1, x + 1)
        self.repl.mv_and_resize(1, self.cols - 4, self.y, self.x + 3)

    def render_panel(self):
        self.win.clear()
        self.win.addstr(self.rows - 1, 1, self.PROMPT)
        self.win.noutrefresh()

        self.repl.render_panel()

    def dispatch_click(self, y, x):
        pass
