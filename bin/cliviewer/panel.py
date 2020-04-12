import curses
import curses.panel
import logging
from abc import ABCMeta, abstractmethod

log = logging.getLogger("Panel")


class PanelContainer(object):
    __metaclass__ = ABCMeta

    def __init__(self, render_lock, rows, cols, y, x):
        self.render_lock = render_lock
        self.panels = {}
        self.focus = 0

        self.c_win = curses.newwin(rows, cols, y, x)
        self.c_win.leaveok(True)

        self.c_panel = curses.panel.new_panel(self.c_win)
        self.c_panel.hide()

        self.rows = rows
        self.cols = cols
        self.y = y
        self.x = x

    @abstractmethod
    def render_container(self):
        raise NotImplementedError("Must be implemented by child class!")

    def mv_and_resize(self, rows, cols, y, x):
        self.rows = rows
        self.cols = cols
        self.y = y
        self.x = x

        self.c_win.resize(self.rows, self.cols)
        self.c_win.mvwin(self.y, self.x)

        for panel in self.panels:
            self.panels[panel].mv_and_resize(self.rows, self.cols, self.y, self.x)

    def dispatch_double_click(self, y, x):
        pass

    @abstractmethod
    def add_panel(self, panel_name, panel_id):
        raise NotImplementedError("Must be implemented by child class!")

    @abstractmethod
    def dispatch_click(self, y, x):
        raise NotImplementedError("Must be implemented by child class!")


class Panel(object):
    __metaclass__ = ABCMeta

    def __init__(self, render_lock, rows, cols, y, x):
        self.render_lock = render_lock

        self.rows = rows
        self.cols = cols
        self.y = y
        self.x = x

        self.win = curses.newwin(rows, cols, y, x)
        self.panel = curses.panel.new_panel(self.win)

    def mv_and_resize(self, rows, cols, y, x):
        self.rows = rows
        self.cols = cols
        self.y = y
        self.x = x

        try:
            self.win.resize(self.rows, self.cols)
            self.win.mvwin(self.y, self.x)
        except curses.error:
            pass

    @abstractmethod
    def render_panel(self):
        raise NotImplementedError("Must be implemented by child class!")

    def dispatch_double_click(self, y, x):
        pass

    @abstractmethod
    def dispatch_click(self, y, x):
        raise NotImplementedError("Must be implemented by child class!")

    def got_clicked(self, y, x):
        return self.win.enclose(y, x)
