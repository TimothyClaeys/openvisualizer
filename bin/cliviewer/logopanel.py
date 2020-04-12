import curses
import curses.panel
import locale
import logging

from panel import Panel, PanelContainer

log = logging.getLogger("LogoPanel")

locale.setlocale(locale.LC_ALL, '')

code = locale.getpreferredencoding()


class LogoPanelContainer(PanelContainer):

    def __init__(self, rows, cols, y, x, render_lock):
        super(LogoPanelContainer, self).__init__(rows, cols, y, x, render_lock)

    def render_container(self):
        self.c_win.clear()
        self.c_win.border()

        self.c_panel.bottom()
        curses.panel.update_panels()

        for key in self.panels:
            self.panels[key].render_panel()

        with self.render_lock:
            self.c_win.refresh()

    def dispatch_click(self, y, x):
        pass

    def add_panel(self, panel_name=None, panel_id=0):
        t = LogoPanel(self.render_lock, self.rows - 2, self.cols - 2, self.y + 1, self.x + 1)
        self.panels[panel_id] = t


class LogoPanel(Panel):
    CALI = "         Berkeley - California       "
    LOGO = \
        " ___                 _ _ _  ___  _ _ " \
        "| . | ___  ___ ._ _ | | | |/ __>| \ |" \
        "| | || . \/ ._>| ' || | | |\__ \|   |" \
        "`___'|  _/\___.|_|_||__/_/ <___/|_\_|" \
        "     |_|                  openwsn.org"

    def __init__(self, render_lock, rows, cols, y, x):
        super(LogoPanel, self).__init__(render_lock, rows, cols, y, x)
        self.win.leaveok(True)

    def render_panel(self):
        self.win.clear()
        try:
            self.win.addstr(self.CALI, curses.A_BOLD)
            self.win.addstr(self.LOGO, curses.A_BOLD)
        except curses.error:
            pass

        self.panel.top()
        curses.panel.update_panels()

    def dispatch_click(self, y, x):
        pass

    def mv_and_resize(self, rows, cols, y, x):
        self.rows = rows - 2
        self.cols = cols - 2
        self.y = y + 1
        self.x = x + 1

        self.win.resize(self.rows, self.cols)
        self.win.mvwin(self.y, self.x)
