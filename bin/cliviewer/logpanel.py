import curses
import curses.panel
import locale
import logging
from collections import deque

from math import ceil

from colors import Elements
from panel import Panel, PanelContainer

log = logging.getLogger("LogPanel")

locale.setlocale(locale.LC_ALL, '')

code = locale.getpreferredencoding()


class LogPanelContainer(PanelContainer):
    TITLE = "Loggers"
    TABS_H = 3
    PANEL = 0
    TAB = 1

    def __init__(self, render_lock, rows, cols, y, x):
        super(LogPanelContainer, self).__init__(render_lock, rows, cols, y, x)
        self.tab_shift = self.x + len(self.TITLE) + 3

    def render_container(self):
        self.c_win.clear()
        self.c_win.addstr(1, 2, self.TITLE, curses.A_STANDOUT)

        self.c_panel.bottom()
        curses.panel.update_panels()

        for key in self.panels:
            logger, tab = self.panels[key]
            tab.render_panel()
            logger.hide()

        self.panels[self.focus][self.PANEL].render_panel()
        self.panels[self.focus][self.TAB].render_panel()

        with self.render_lock:
            curses.doupdate()

    def scroll(self, scroll_dir):
        self.panels[self.focus][self.PANEL].scroll(scroll_dir)
        self.panels[self.focus][self.TAB].render_panel()

        with self.render_lock:
            curses.doupdate()

    def mv_and_resize(self, rows, cols, y, x):
        self.rows = rows
        self.cols = cols
        self.y = y
        self.x = x

        self.c_win.resize(self.rows, self.cols)
        self.c_win.mvwin(self.y, self.x)

        for key in self.panels:
            self.panels[key][self.PANEL].mv_and_resize(rows - self.TABS_H + 1, cols, y + self.TABS_H - 1, x)
            self.panels[key][self.TAB].mv_and_resize(rows, cols, y, x)

    def dispatch_double_click(self, y, x):
        for key in self.panels:
            if self.panels[key][self.PANEL].got_clicked(y, x):
                self.panels[key][self.PANEL].dispatch_double_click(y, x)

    def dispatch_click(self, y, x):
        panel = None
        for key in self.panels:
            if self.panels[key][self.TAB].got_clicked(y, x):
                self.focus = key
                panel = key
                break

        if panel is None:
            return

        for key in self.panels:
            self.panels[key][self.PANEL].hide()

        self.panels[self.focus][self.PANEL].dispatch_click(y, x)
        self.panels[self.focus][self.TAB].dispatch_click(y, x)

    def add_panel(self, panel_name, panel_id, col_num=0):
        lv = LogPanel(self.render_lock, self.rows - self.TABS_H + 1, self.cols, self.y + self.TABS_H - 1, self.x,
                      panel_name)
        tab = Tab(self.render_lock, self.TABS_H, len(panel_name) + 2, 0, self.tab_shift, panel_name, col_num)
        self.tab_shift += len(panel_name) + 2
        self.panels[panel_id] = (lv, tab)

    def dispatch_log(self, msg, mote_id, level):
        try:
            if int(mote_id) != 0:
                self.panels[0][self.PANEL].add_log(msg, level)
            self.panels[int(mote_id)][self.PANEL].add_log(msg, level)

            for key in self.panels:
                if key != self.focus:
                    self.panels[key][self.PANEL].hide()

            if int(mote_id) == int(self.focus):
                self.panels[self.focus][self.PANEL].render_panel()
                self.panels[self.focus][self.TAB].render_panel()

            if self.c_win.is_wintouched:
                with self.render_lock:
                    curses.doupdate()

        except KeyError:
            log.error("Mote ID ({}) did not match with a log panel ID".format(mote_id))


class Tab(Panel):
    def __init__(self, render_lock, rows, cols, y, x, name, color):
        super(Tab, self).__init__(render_lock, rows, cols, y, x)
        self.name = name
        self.color = color
        self.win.leaveok(True)

    def mv_and_resize(self, rows, cols, y, x):
        try:
            super(Tab, self).mv_and_resize(self.rows, self.cols, self.y, self.x)
        except curses.error:
            pass

    def render_panel(self):
        self.win.clear()

        attr = curses.color_pair(self.color)
        if self.color != 0:
            attr |= curses.A_REVERSE

        try:
            self.win.border(curses.ACS_VLINE, curses.ACS_VLINE, curses.ACS_HLINE, ' ', curses.ACS_ULCORNER,
                            curses.ACS_URCORNER, curses.ACS_LRCORNER, curses.ACS_LLCORNER)
            self.win.addstr(1, 1, self.name, attr)
        except curses.error:
            pass

        self.panel.top()
        curses.panel.update_panels()

    def dispatch_click(self, y, x):
        self.render_panel()


class LogPanel(Panel):
    ARROW_DOWN = u'\u25bc'.encode(code)
    ARROW_UP = u'\u25b2'.encode(code)
    DIAMOND = u'\u25c6'.encode(code)

    def __init__(self, lock, rows, cols, y, x, name):
        super(LogPanel, self).__init__(lock, rows, cols, y, x)
        self.name = name
        self.win.leaveok(True)

        self.logs = deque()
        self.scroll_offset = 0

        self.statusbar = self.win.derwin(1, self.cols - 2, self.rows - 2, 1)
        self.statusbar.bkgd(' ', curses.color_pair(Elements.STATUSBAR))
        self.statusbar.leaveok(True)

        self.scrollup = self.win.derwin(3, 2, 1, self.cols - 3)
        self.scrollup.bkgd(' ', curses.color_pair(Elements.BUTTON) | curses.A_REVERSE)
        self.scrollup.leaveok(True)
        self.scrolldw = self.win.derwin(3, 2, self.rows - 6, self.cols - 3)
        self.scrolldw.bkgd(' ', curses.color_pair(Elements.BUTTON) | curses.A_REVERSE)
        self.scrolldw.leaveok(True)
        self.scrollbar = self.win.derwin(self.rows - 9, 2, 4, self.cols - 3)
        self.scrollbar.bkgd(' ', curses.color_pair(Elements.BUTTON) | curses.A_REVERSE)
        self.scrollbar.leaveok(True)

        self.canvas = self.win.derwin(self.rows - 4, self.cols - 5, 1, 1)
        self.canvas.scrollok(True)
        self.canvas.idlok(True)
        self.canvas.leaveok(True)

    def scroll(self, scroll_dir):
        self.scroll_offset += scroll_dir
        if self.scroll_offset < 0:
            self.scroll_offset = 0
        self.render_panel()

    def hide(self):
        self.panel.hide()
        curses.panel.update_panels()

    def got_clicked(self, y, x):
        return super(LogPanel, self).got_clicked(y, x) and not self.panel.hidden()

    def add_log(self, msg, level):
        self.logs.append(msg)

    def dispatch_click(self, y, x):
        self.render_panel()

    def dispatch_double_click(self, y, x):
        pass

    def mv_and_resize(self, rows, cols, y, x):
        super(LogPanel, self).mv_and_resize(rows, cols, y, x)
        self.win.clear()
        self.statusbar.clear()
        self.scrollup.clear()
        self.scrolldw.clear()
        self.canvas.clear()

        self.scrollup.mvderwin(1, self.cols - 3)
        self.scrollup.resize(3, 2)

        self.scrolldw.mvderwin(self.rows - 6, self.cols - 3)
        self.scrolldw.resize(3, 2)

        self.scrollbar.mvderwin(1 + 3, self.cols - 3)
        self.scrollbar.resize(self.rows - 6 - 3, 2)

        self.canvas.resize(self.rows - 4, self.cols - 5)
        self.canvas.mvderwin(1, 1)

        self.statusbar.resize(1, self.cols - 2)
        self.statusbar.mvderwin(self.rows - 2, 1)

    def render_panel(self):
        self.win.clear()
        self.win.border()

        self._render_scrollbar()
        self._render_logs()

        self.panel.top()
        curses.panel.update_panels()

    def _render_logs(self):
        self.canvas.clear()

        rows, cols = self.canvas.getmaxyx()
        recent_logs = list(self.logs)[-rows - self.scroll_offset:len(self.logs) - self.scroll_offset]
        for log_line in recent_logs:
            try:
                self.canvas.addstr(log_line)
            except curses.error:
                pass

        self._render_statusbar()
        self.canvas.noutrefresh()

    def _render_scrollbar(self):
        self.scrollup.clear()
        self.scrolldw.clear()
        self.scrollbar.clear()

        rows, _ = self.scrollbar.getmaxyx()
        try:
            y = int(ceil(((len(self.logs) - self.scroll_offset) / (len(self.logs) * 1.0)) * rows))
        except ZeroDivisionError:
            y = 0

        y -= 2

        if y < 0:
            y = 0

        try:
            self.scrollbar.addstr(y, 0, self.DIAMOND)
            self.scrollup.addstr(' '.join([self.ARROW_UP] * 3))
            self.scrolldw.addstr(' '.join([self.ARROW_DOWN] * 3))
        except curses.error:
            pass

        self.scrollbar.noutrefresh()
        self.scrollup.noutrefresh()
        self.scrolldw.noutrefresh()

    def _render_statusbar(self):
        self.statusbar.clear()

        try:
            self.statusbar.addstr(
                "   STATUS   {}  --  (INFO: {})   (ERRORS: {})   (CRITICAL: {})  |  SCROLL: {}/{}".format(
                    self.name, 0, 0, 0, len(self.logs) - self.scroll_offset, len(self.logs)))
        except curses.error:
            pass

        self.statusbar.noutrefresh()
