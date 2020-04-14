import curses
import curses.textpad
import logging
import threading
from random import randint

from cmdpanel import CmdPanelContainer
from colors import Elements, MoteColors, ColorPairsMote, MoteColorsDim, ColorPairsMoteDim
from logopanel import LogoPanelContainer
from logpanel import LogPanelContainer
from sidepanel import SidePanelContainer

log = logging.getLogger('TerminalViewer')


class TermViewer:
    # dimensions windows
    CMD_HISTORY = 0
    INPUT_BOX_H = CMD_HISTORY + 3
    LOGO_HEIGTH = 8
    SIDE_BOX_W = 39

    # printable strings
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.stdscr.leaveok(True)

        # get current sizes of the terminal pawin
        self.rows, self.cols = self.stdscr.getmaxyx()

        self.render_lock = threading.Lock()
        self.motes = {}
        self.focus = 0

        # panel storage
        self.lpc = None
        self.repl = None
        self.spc = None
        self.logo = None

        self.clickable = []

        self._create_logo_window()
        self._create_log_window()
        self._create_side_window()
        self._create_repl_window()

        # colors
        curses.init_pair(ColorPairsMote.P_RED_B, curses.COLOR_BLACK, MoteColors.RED)
        curses.init_pair(ColorPairsMote.P_PINK_B, curses.COLOR_BLACK, MoteColors.PINK)
        curses.init_pair(ColorPairsMote.P_ROSE_B, curses.COLOR_BLACK, MoteColors.ROSE)
        curses.init_pair(ColorPairsMote.P_GOLD_B, curses.COLOR_BLACK, MoteColors.GOLD)
        curses.init_pair(ColorPairsMote.P_GREEN_B, curses.COLOR_BLACK, MoteColors.GREEN)
        curses.init_pair(ColorPairsMote.P_LBLUE_B, curses.COLOR_BLACK, MoteColors.LBLUE)
        curses.init_pair(ColorPairsMote.P_BLUE_B, curses.COLOR_BLACK, MoteColors.BLUE)
        curses.init_pair(ColorPairsMote.P_DBLUE_B, curses.COLOR_BLACK, MoteColors.DBLUE)
        curses.init_pair(ColorPairsMote.P_PURPLE_B, curses.COLOR_BLACK, MoteColors.PURPLE)
        curses.init_pair(ColorPairsMote.P_SKIN_B, curses.COLOR_BLACK, MoteColors.SKIN)

        curses.init_pair(ColorPairsMoteDim.P_RED_B, curses.COLOR_BLACK, MoteColorsDim.RED)
        curses.init_pair(ColorPairsMoteDim.P_PINK_B, curses.COLOR_BLACK, MoteColorsDim.PINK)
        curses.init_pair(ColorPairsMoteDim.P_ROSE_B, curses.COLOR_BLACK, MoteColorsDim.ROSE)
        curses.init_pair(ColorPairsMoteDim.P_GOLD_B, curses.COLOR_BLACK, MoteColorsDim.GOLD)
        curses.init_pair(ColorPairsMoteDim.P_GREEN_B, curses.COLOR_BLACK, MoteColorsDim.GREEN)
        curses.init_pair(ColorPairsMoteDim.P_LBLUE_B, curses.COLOR_BLACK, MoteColorsDim.LBLUE)
        curses.init_pair(ColorPairsMoteDim.P_BLUE_B, curses.COLOR_BLACK, MoteColorsDim.BLUE)
        curses.init_pair(ColorPairsMoteDim.P_DBLUE_B, curses.COLOR_BLACK, MoteColorsDim.DBLUE)
        curses.init_pair(ColorPairsMoteDim.P_PURPLE_B, curses.COLOR_BLACK, MoteColorsDim.PURPLE)
        curses.init_pair(ColorPairsMoteDim.P_SKIN_B, curses.COLOR_BLACK, MoteColorsDim.SKIN)

        # more colors
        curses.init_pair(Elements.STATUSBAR, curses.COLOR_BLACK, 156)
        curses.init_pair(Elements.BUTTON, curses.COLOR_BLACK, 172)

        self.render_content()

    def add_content(self, motes):
        self.motes = motes

        log.info("Connected motes: {}".format(self.motes))

        offset = randint(1, len(ColorPairsMote))
        for i, key in enumerate(self.motes):
            name = " Mote: {} ".format(str(key))
            color = (offset + i) % len(ColorPairsMote) + 1
            self.lpc.add_panel(name, int(key, 16), color)
            self.spc.add_panel(name, int(key, 16), color)

        self.render_content()

    def render_content(self):

        self.lpc.render_container()
        self.repl.render_container()
        self.logo.render_container()
        self.spc.render_container()

    def rerender(self):
        self.rows, self.cols = self.stdscr.getmaxyx()

        rows_lpc = self.rows - self.INPUT_BOX_H
        cols_lpc = self.cols - self.SIDE_BOX_W

        y_repl = self.rows - self.INPUT_BOX_H

        rows_spc = self.rows - self.INPUT_BOX_H - self.LOGO_HEIGTH

        if rows_lpc < 1 or cols_lpc < 1 or self.rows <= self.INPUT_BOX_H + 5 or rows_spc < 1:
            return

        self.lpc.mv_and_resize(rows_lpc, cols_lpc, 0, self.SIDE_BOX_W)
        self.repl.mv_and_resize(self.INPUT_BOX_H, self.cols, y_repl, 0)
        self.logo.mv_and_resize(self.LOGO_HEIGTH, self.SIDE_BOX_W, 0, 0)
        self.spc.mv_and_resize(rows_spc, self.SIDE_BOX_W, self.LOGO_HEIGTH, 0)

        # rebuild the content
        self.render_content()

    def handle_mouse_event(self):
        try:
            _, x, y, _, bstate = curses.getmouse()
        except curses.error:
            log.error('Illegal mouse event')
            return

        if bstate == curses.BUTTON1_CLICKED:
            for item in self.clickable:
                if item.dispatch_click(y, x):
                    break
        elif bstate == curses.BUTTON1_DOUBLE_CLICKED:
            for item in self.clickable:
                if item.dispatch_double_click(y, x):
                    break

    def scroll(self, dir):
        self.lpc.scroll(dir)

    # private functions

    def _create_log_window(self):
        rows = self.rows - self.INPUT_BOX_H
        cols = self.cols - self.SIDE_BOX_W

        self.lpc = LogPanelContainer(self.render_lock, rows, cols, 0, self.SIDE_BOX_W)
        self.lpc.add_panel(" ALL ", 0)
        self.clickable.append(self.lpc)

    def _create_repl_window(self):
        # set up repl zone
        y = self.rows - self.INPUT_BOX_H
        self.repl = CmdPanelContainer(self.render_lock, self.INPUT_BOX_H, self.cols, y, 0)
        self.repl.add_panel()

    def _create_logo_window(self):
        self.logo = LogoPanelContainer(self.render_lock, self.LOGO_HEIGTH, self.SIDE_BOX_W, 0, 0)
        self.logo.add_panel()

    def _create_side_window(self):
        rows = self.rows - self.INPUT_BOX_H - self.LOGO_HEIGTH
        self.spc = SidePanelContainer(self.render_lock, rows, self.SIDE_BOX_W, self.LOGO_HEIGTH, 0)
        self.clickable.append(self.spc)
