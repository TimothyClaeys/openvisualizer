import curses
import json
import locale
import logging
import threading

import time

from openvisualizer.motehandler.motestate.motestate import MoteState as ms
from panel import PanelContainer, Panel

locale.setlocale(locale.LC_ALL, '')

code = locale.getpreferredencoding()

log = logging.getLogger("SidePanel")


class SidePanelContainer(PanelContainer):
    TITLE = " Mote Viewer "
    BTN_MARGIN = 4

    def __init__(self, render_lock, rows, cols, y, x):
        super(SidePanelContainer, self).__init__(render_lock, rows, cols, y, x)
        self.panel_shift = 0
        self.motes_visible = None

    def mv_and_resize(self, rows, cols, y, x):
        super(SidePanelContainer, self).mv_and_resize(rows, cols, y, x)

        for key in self.panels:
            self.panels[key].set_container_size(self.rows, self.cols)

        self.motes_visible = self.panels.keys()[:self.rows - self.BTN_MARGIN]

        log.debug(self.motes_visible)

    def render_container(self):
        self.c_win.clear()
        self.c_win.border()
        self.c_win.addstr(0, int(self.cols / 2 - len(self.TITLE) / 2), self.TITLE, curses.A_STANDOUT)
        self.c_win.noutrefresh()

        if self.motes_visible is not None:
            for shift, key in enumerate(self.motes_visible):
                self.panels[key].render_panel(offset=shift)

        with self.render_lock:
            curses.doupdate()

    def dispatch_click(self, y, x):
        panel = None

        for s, key in enumerate(self.motes_visible):
            if self.panels[key].got_clicked(y, x):
                panel = key
                break

        if panel is None:
            return

        if not self.panels[panel].dispatch_click(y, x):
            self.panels[panel].render_panel()

            with self.render_lock:
                curses.doupdate()
        else:
            self.render_container()

    def add_panel(self, panel_name, panel_id, color=0):
        sp = SidePanel(self.render_lock, 1, self.cols - 2, self.y + 1, self.x + 1, panel_name, self.panel_shift, color)
        self.panel_shift += 1
        self.panels[panel_id] = sp
        self.panels[panel_id].set_container_size(self.rows, self.cols)

        self.motes_visible = self.panels.keys()[:self.rows - self.BTN_MARGIN]
        log.debug(self.motes_visible)

    def renew_mote_state(self, mote_id, mote_state):
        try:
            self.panels[mote_id].update_state(mote_state)
        except KeyError:
            log.error("Couldn't update mote state, mote {} has no panel".format(mote_id))


class SidePanel(Panel):
    ARROW_DOWN = u'\u25bc'.encode(code)
    ARROW_UP = u'\u25b2'.encode(code)
    DIAMOND = u'\u2b25'.encode(code)

    def __init__(self, render_lock, rows, cols, y, x, panel_name, mote_num, col_num):
        super(SidePanel, self).__init__(render_lock, rows, cols, y, x)
        self.mote_num = mote_num
        self.col_num = col_num
        self.name = " {:02d}. {}".format(self.mote_num + 1, panel_name)

        self.win.bkgd(" ", curses.color_pair(self.col_num))
        self.win.leaveok(True)

        self.folded = True
        self.c_rows = 0
        self.c_cols = 0

        self.status = None
        self.state_thread = None
        self.state_functions = \
            [
                self._get_dagroot,
                self._get_prefix,
                self._get_addr_64b,
                self._get_pan_id
            ]

    def got_clicked(self, y, x):
        return super(SidePanel, self).got_clicked(y, x)

    def set_container_size(self, c_rows, c_cols):
        self.c_rows = c_rows
        self.c_cols = c_cols

    def render_panel(self, offset=0):
        self.win.clear()
        self.win.mvwin(self.y + offset, self.x)
        self.win.addstr(self.name)

        if self.folded:
            self.win.addstr(0, self.cols - 3, self.ARROW_DOWN)
        else:
            self.win.addstr(0, self.cols - 3, self.ARROW_UP)
            self._populate_mote_status()

        self.win.noutrefresh()

    def mv_and_resize(self, rows, cols, y, x):
        super(SidePanel, self).mv_and_resize(1, cols - 2, y + 1, x + 1)
        # close all mote detail panels
        self.folded = True

    def dispatch_click(self, y, x):
        self.folded = not self.folded

        if not self.folded:
            self.rows = self.c_rows - 2
            self.cols = self.c_cols - 2
            self.win.resize(self.c_rows - 2, self.c_cols - 2)
            self.win.mvwin(self.y, self.x)
        else:
            self.rows = 1
            self.state_thread.join()
            self.win.resize(self.rows, self.cols)
            self.win.mvwin(self.y, self.x)

        return self.folded

    def update_state(self, mote_status):
        self.status = mote_status

    # private functions

    def _populate_mote_status(self):
        self.state_thread = threading.Thread(target=self._updater)
        rows, cols = self.win.getmaxyx()
        self.state_panel = self.win.derwin(rows - 2, cols, 1, 0)
        self.state_panel.bkgd(' ', curses.color_pair(self.col_num + 10))
        self.state_thread.start()

    def _updater(self):
        while not self.folded:
            self.state_panel.clear()
            idm = json.loads(self.status[ms.ST_IDMANAGER])

            for func in self.state_functions:
                try:
                    func(idm)
                except curses.error:
                    pass

            self.state_panel.noutrefresh()
            with self.render_lock:
                curses.doupdate()

            time.sleep(0.1)

    def _get_dagroot(self, idm):
        self.state_panel.addstr(1, 1, self.DIAMOND)
        self.state_panel.addstr(1, 3, 'DAGroot:', curses.A_UNDERLINE)
        self.state_panel.addstr(1, 3 + len('DAGroot:') + 1, '{}'.format(idm[0]["isDAGroot"]))

    def _get_prefix(self, idm):
        self.state_panel.addstr(2, 1, self.DIAMOND)
        self.state_panel.addstr(2, 3, 'Prefix:', curses.A_UNDERLINE)
        self.state_panel.addstr(2, 3 + len('Prefix:') + 1, '{}'.format(idm[0]["myPrefix"][:-9]))

    def _get_addr_64b(self, idm):
        self.state_panel.addstr(3, 1, self.DIAMOND)
        self.state_panel.addstr(3, 3, 'ADDR 64b:', curses.A_UNDERLINE)
        self.state_panel.addstr(3, 3 + len('ADDR 64b:') + 1, '{}'.format(idm[0]["my64bID"][:-6]))

    def _get_pan_id(self, idm):
        self.state_panel.addstr(4, 1, self.DIAMOND)
        self.state_panel.addstr(4, 3, 'PAN ID:', curses.A_UNDERLINE)
        self.state_panel.addstr(4, 3 + len('PAN ID:') + 1, '{}'.format(idm[0]["myPANID"][:-8]))
