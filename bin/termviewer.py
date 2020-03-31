import curses
import curses.textpad
import locale
import logging.handlers
import re
import sys
from collections import deque

locale.setlocale(locale.LC_ALL, '')

code = locale.getpreferredencoding()

log = logging.getLogger('TerminalViewer')


class CursesHandler(logging.Handler):
    def __init__(self):
        super(CursesHandler, self).__init__()
        self._screen = None

    @property
    def screen(self):
        if self._screen is None:
            raise ValueError("Screen not initialized")
        return self._screen

    @screen.setter
    def screen(self, new_screen):
        self._screen = new_screen

    @classmethod
    def extract_mote_id(cls, msg):
        try:
            m = re.search(r'^([0-9a-zA-Z]{1,4}) .*', msg)
            if m is not None:
                return int(m.group(1), 16)
            else:
                return 0
        except ValueError:
            return 0

    def emit(self, record):
        try:
            level = record.levelname
            mote_id = CursesHandler.extract_mote_id(record.message)
            msg = self.format(record)
            fs = "{}\n".format(msg)
            self.screen.add_to_logs(fs, level, mote_id)
        except Exception as err:
            print err
            sys.exit(1)


logging.handlers.CursesHandler = CursesHandler


class TermViewer:
    # coordinates windows
    CMD_HISTORY = 4
    LOG_HISTORY = 500
    BTN_BAR = 3
    INPUT_BOX_HEIGHT = CMD_HISTORY + 4
    LOGO_HEIGTH = 7
    SIDE_PANEL_WIDTH = 39

    # printable strings
    LOADING = "LOADING OPENVISUALIZER..."
    PROMPT = '> '
    TITLE_LOGGER = "INCOMING LOGS"
    BTN_ALL_LOGS = "ALL"
    BTN_MOTE = "MOTE {}"
    LOGO = \
        " ___                 _ _ _  ___  _ _ " \
        "| . | ___  ___ ._ _ | | | |/ __>| \ |" \
        "| | || . \/ ._>| ' || | | |\__ \|   |" \
        "`___'|  _/\___.|_|_||__/_/ <___/|_\_|" \
        "     |_|                  openwsn.org"

    # ids and dict keys
    ALL_LOGS = 0
    LQ = 0
    PLEN = 1
    SCROLL_UP = 0
    SCROLL_DOWN = 1

    # unicode chars
    ARROW_UP = u'\u2191'.encode(code)
    ARROW_DOWN = u'\u2193'.encode(code)

    def __init__(self, stdscr, lock):
        self.stdscr = stdscr
        self.stdscr.leaveok(True)

        # get current sizes of the terminal window
        self.rows, self.cols = self.stdscr.getmaxyx()

        self.lock = lock
        self.motes_connected = 0
        # all, motes :
        self.logs = {self.ALL_LOGS: [deque(), 0]}

        self.wdw_focus = 0
        self.clickable_btns = []
        self.scrollers = []

        self.log_panel = None

        # initialize color pairs
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_GREEN)
        curses.init_pair(2, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)

        self.stdscr.addstr(int(self.rows / 2), int(self.cols / 2) - int(len(self.LOADING) / 2), self.LOADING,
                           curses.color_pair(3))
        self.stdscr.refresh()

    def renderable(self):
        return self.cols > self.SIDE_PANEL_WIDTH + 2 or self.rows > self.INPUT_BOX_HEIGHT + self.LOGO_HEIGTH + 4

    def update_term_size(self):
        self.rows, self.cols = self.stdscr.getmaxyx()

    def handle_mouse_event(self):
        try:
            _, x, y, _, _ = curses.getmouse()
        except curses.error:
            return

        for btn in self.clickable_btns:
            if btn[0].enclose(y, x) and btn[1] != self.wdw_focus:
                self.wdw_focus = btn[1]
        for btn in self.scrollers:
            if btn[0].enclose(y, x):
                log.info("mouse")
                self._scroll_logs(btn[1])

        self.render_log_window()

    def add_to_logs(self, log, level, mote_id):
        self.lock.acquire()

        if mote_id not in self.logs:
            self.logs[mote_id] = [deque(), 0]

        if len(self.logs[mote_id]) >= self.LOG_HISTORY - 1:
            _ = self.logs[mote_id][self.LQ].popleft()

        if len(self.logs[self.ALL_LOGS]) >= self.LOG_HISTORY - 1:
            _ = self.logs[self.ALL_LOGS][self.LQ].popleft()

        self.logs[mote_id][self.LQ].append((level, log))

        if mote_id != self.ALL_LOGS:
            self.logs[self.ALL_LOGS][self.LQ].append((level, log))

        self.lock.release()
        self._render_logs(full_render=False, new_focus=self.wdw_focus)

    # public rendering functions

    def render_logo(self):
        logo_panel = curses.newwin(self.LOGO_HEIGTH, self.SIDE_PANEL_WIDTH, 0, 0)
        logo_panel.box()

        logo = logo_panel.derwin(self.LOGO_HEIGTH - 1, self.SIDE_PANEL_WIDTH - 2, 1, 1)
        logo.addstr(0, 0, self.LOGO, curses.A_BOLD)

        self.lock.acquire()
        logo_panel.refresh()
        logo.refresh()
        self.lock.release()

    def render_side_panel(self):
        side_panel = curses.newwin(self.rows - self.INPUT_BOX_HEIGHT - self.LOGO_HEIGTH, self.SIDE_PANEL_WIDTH,
                                   self.LOGO_HEIGTH, 0)
        side_panel.border()

        self.lock.acquire()
        side_panel.refresh()
        self.lock.release()

    def render_button_bar(self):
        button_bar_window = curses.newwin(self.BTN_BAR, self.cols - self.SIDE_PANEL_WIDTH, 0, self.SIDE_PANEL_WIDTH)
        column_cnt = 0

        try:
            title = button_bar_window.derwin(self.BTN_BAR, len(self.TITLE_LOGGER) + 2, column_cnt, 0)
            title.addstr(1, 1, self.TITLE_LOGGER, curses.A_STANDOUT)
            column_cnt += len(self.TITLE_LOGGER) + 2

            btn_all = button_bar_window.derwin(self.BTN_BAR, len(self.BTN_ALL_LOGS) + 2, 0, column_cnt)
            btn_all.border()
            btn_all.addstr(1, 1, self.BTN_ALL_LOGS, curses.A_BOLD)
            column_cnt += len(self.BTN_ALL_LOGS) + 2

            # add button and id to list with clickable items
            self.clickable_btns.append((btn_all, 0))

            for mote in range(self.motes_connected):
                btn_name = self.BTN_MOTE.format(mote + 1)
                btn_mote = button_bar_window.derwin(self.BTN_BAR, len(btn_name) + 2, 0, column_cnt)
                btn_mote.border()
                btn_mote.addstr(1, 1, btn_name, curses.A_BOLD)
                column_cnt += len(btn_name) + 2
                self.clickable_btns.append((btn_mote, mote + 1))
        except curses.error:
            pass
        else:
            self.lock.acquire()
            button_bar_window.refresh()
            title.refresh()
            btn_all.refresh()
            self.lock.release()

    def render_log_window(self):
        # location of the log window
        log_window = curses.newwin(self.rows - self.INPUT_BOX_HEIGHT - self.BTN_BAR + 1,
                                   self.cols - self.SIDE_PANEL_WIDTH, self.BTN_BAR - 1,
                                   self.SIDE_PANEL_WIDTH)
        log_window.border()

        self._render_scroller(log_window)

        local_rows, local_cols = log_window.getmaxyx()

        log_state = log_window.derwin(1, local_cols - 2, local_rows - 2, 1)
        log_state.bkgd(' ', curses.color_pair(1))

        try:
            if self.wdw_focus == self.ALL_LOGS:
                log_state.addstr(0, 5, "SHOWING ALL LOGS", curses.A_BOLD)
                log_state.addstr(0, 5 + len("SHOWING ALL LOGS  "), '(INFO: 0) (ERROR: 0) (CRITICAL: 0)')
        except curses.error:
            pass

        try:
            active_btn = self.clickable_btns[self.wdw_focus][0]
            active_btn.border(curses.ACS_VLINE, curses.ACS_VLINE, curses.ACS_HLINE, ' ', curses.ACS_ULCORNER,
                              curses.ACS_URCORNER, curses.ACS_LRCORNER, curses.ACS_LLCORNER)
        except IndexError:
            self.lock.acquire()
            log_window.refresh()
            log_state.refresh()
        else:
            self.lock.acquire()
            log_window.refresh()
            active_btn.refresh()
            log_state.refresh()
        self.lock.release()

        local_rows, local_cols = log_window.getmaxyx()
        self.log_panel = log_window.derwin(local_rows - 3, local_cols - 3, 1, 1)
        self.log_panel.scrollok(True)
        self.log_panel.idlok(True)
        self.log_panel.leaveok(True)
        self._render_logs(full_render=True)

    def render_input_area(self, history=None):
        # set up repl zone
        repl_window = curses.newwin(self.INPUT_BOX_HEIGHT, self.cols, self.rows - self.INPUT_BOX_HEIGHT, 0)
        repl_window.border()
        repl_window.addstr(self.INPUT_BOX_HEIGHT - 2, 2, self.PROMPT)

        local_rows, local_cols = repl_window.getmaxyx()

        # set up command cmd_history zone
        if self.CMD_HISTORY > 0 and history is not None:
            cmd_window = repl_window.derwin(self.CMD_HISTORY, local_cols - 2, 1, 1)
            self._render_cmd_history(history, cmd_window)
            self.lock.acquire()
            cmd_window.refresh()
            self.lock.release()

        # set up user input zone
        input_line = repl_window.derwin(1, local_cols - 5, self.INPUT_BOX_HEIGHT - 2, 4)
        input_line.nodelay(True)

        input_line.move(0, 0)
        input_line.clear()

        self.lock.acquire()
        repl_window.refresh()
        input_line.refresh()
        self.lock.release()

        input_box = curses.textpad.Textbox(input_line)
        input_box.stripspaces = True

        return input_box

    # private rendering functions

    def _render_cmd_history(self, history, cmd_window):
        if self.CMD_HISTORY <= 0:
            return

        cmd_window.erase()
        for i in range(len(history)):
            cmd = history.popleft()
            cmd_window.addstr(0 + i, 1, cmd)
            history.append(cmd)

        self.lock.acquire()
        cmd_window.refresh()
        self.lock.release()

    def _render_logs(self, full_render=False, new_focus=None):
        if new_focus is None:
            new_focus = self.wdw_focus

        if self.log_panel is None:
            # no log panel defined, cannot paint
            return

        rows, cols = self.log_panel.getmaxyx()

        self.lock.acquire()
        if full_render or self.wdw_focus != new_focus:
            self.logs[self.wdw_focus][self.PLEN] = len(self.logs[self.wdw_focus][self.LQ])
            self.wdw_focus = new_focus
            self.log_panel.clear()

            if len(self.logs[self.wdw_focus][self.LQ]) > rows:
                recent_logs = list(self.logs[self.wdw_focus][self.LQ])[-rows:]
                for log_line in recent_logs:
                    if log_line[0] == 'ERROR':
                        self.log_panel.addstr(log_line[1], curses.color_pair(4))
                    else:
                        self.log_panel.addstr(log_line[1])
            else:
                for i in range(len(self.logs[self.wdw_focus][self.LQ])):
                    log_line = self.logs[self.wdw_focus][self.LQ].popleft()
                    if log_line[0] == 'ERROR':
                        self.log_panel.addstr(log_line[1], curses.color_pair(4))
                    else:
                        self.log_panel.addstr(log_line[1])
                    self.logs[self.wdw_focus][self.LQ].append(log_line)

        elif len(self.logs[self.wdw_focus][self.LQ]) != self.logs[self.wdw_focus][self.PLEN]:
            self.logs[self.wdw_focus][self.PLEN] = len(self.logs[self.wdw_focus][self.LQ])

            try:
                log_line = self.logs[self.wdw_focus][self.LQ].pop()
            except IndexError:
                pass
            else:
                if log_line[0] == 'ERROR':
                    self.log_panel.addstr(log_line[1], curses.color_pair(4))
                else:
                    self.log_panel.addstr(log_line[1])
                self.logs[self.wdw_focus][self.LQ].append(log_line)

        self.log_panel.refresh()
        self.lock.release()

    def _render_scroller(self, log_window):
        rows, cols = log_window.getmaxyx()
        scroll_bar_up = log_window.derwin(4, 1, 1, cols - 2)
        scroll_bar_down = log_window.derwin(4, 1, rows - 6, cols - 2)

        self.scrollers.extend([(scroll_bar_up, self.SCROLL_UP), (scroll_bar_down, self.SCROLL_DOWN)])

        for i in range(3):
            scroll_bar_up.addstr(i, 0, self.ARROW_UP, curses.color_pair(2) | curses.A_BOLD)
            scroll_bar_down.addstr(i, 0, self.ARROW_DOWN, curses.color_pair(2) | curses.A_BOLD)

        self.lock.acquire()
        scroll_bar_up.refresh()
        scroll_bar_down.refresh()
        self.lock.release()

    def _scroll_logs(self, direction):
        pass
