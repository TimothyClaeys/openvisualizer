#!/usr/bin/env python

# Copyright (c) 2010-2013, Regents of the University of California. 
# All rights reserved. 
#  
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License

import curses
import logging
import logging.config
import os
import threading
from argparse import ArgumentParser
from cmd import Cmd
from collections import deque

import bottle
import signal
import time

# do not remove line below, prevents PyCharm optimizing out the next import
# noinspection PyUnresolvedReferences
import build_python_path
import openvisualizer_app
import utils as u
from cliviewer.termviewer import TermViewer
from cliviewer.logdispatcher import LogDispatcher
from openvisualizer.motehandler.motestate.motestate import MoteState
from webserver import WebServer

log = logging.getLogger('OpenVisualizerCli')


def signal_handler(sig, frame):
    log.warning('You pressed Ctrl+C! Close with the \'quit\' command')


signal.signal(signal.SIGINT, signal_handler)


class Cli(Cmd):
    ENTER = 10

    def __init__(self, app, viewer):
        log.debug('create instance')

        # since Cmd is an old-style class, can't use super() here
        Cmd.__init__(self)

        # store params
        self.app = app
        self.debug = False

        # terminal interface
        self.viewer = viewer
        self.input_box = None
        self.cmd_history = deque()

        self.found_motes = False
        self.quit = False

        self.t = threading.Thread(target=self.mote_updater)
        self.t.start()

    def discover_motes(self):
        motes = self.app.get_mote_dict().values()
        while None in motes:
            motes = self.app.get_mote_dict().values()

        self.viewer.add_content(sorted(self.app.get_mote_dict()))

        self.found_motes = True

    def validator(self, key):
        # check pawin resize
        if curses.is_term_resized(self.viewer.rows, self.viewer.cols):
            # redraw everything
            self.viewer.rerender()
            return False

        # fix to capture osx backspace key
        if key == curses.KEY_BACKSPACE or str(key) == '127':
            return curses.KEY_BACKSPACE
        elif key == curses.KEY_MOUSE:
            self.viewer.handle_mouse_event()
            return key
        elif key == curses.KEY_UP:
            self.viewer.scroll(+1)
            return False
        elif key == curses.KEY_DOWN:
            self.viewer.scroll(-1)
            return False
        elif 127 < key < 32:
            return False
        else:
            return key

    def mote_updater(self):
        while not self.quit:
            time.sleep(0.5)

            if not self.found_motes:
                continue

            for mote in self.viewer.motes:
                ms = self.app.get_mote_state(mote)
                if ms:
                    state = \
                        {
                            ms.ST_IDMANAGER: ms.get_state_elem(ms.ST_IDMANAGER).to_json('data'),
                            ms.ST_ASN: ms.get_state_elem(ms.ST_ASN).to_json('data'),
                            ms.ST_ISSYNC: ms.get_state_elem(ms.ST_ISSYNC).to_json('data'),
                            ms.ST_MYDAGRANK: ms.get_state_elem(ms.ST_MYDAGRANK).to_json('data'),
                            ms.ST_KAPERIOD: ms.get_state_elem(ms.ST_KAPERIOD).to_json('data'),
                            ms.ST_OUPUTBUFFER: ms.get_state_elem(ms.ST_OUPUTBUFFER).to_json('data'),
                            ms.ST_BACKOFF: ms.get_state_elem(ms.ST_BACKOFF).to_json('data'),
                            ms.ST_MACSTATS: ms.get_state_elem(ms.ST_MACSTATS).to_json('data'),
                            ms.ST_SCHEDULE: ms.get_state_elem(ms.ST_SCHEDULE).to_json('data'),
                            ms.ST_QUEUE: ms.get_state_elem(ms.ST_QUEUE).to_json('data'),
                            ms.ST_NEIGHBORS: ms.get_state_elem(ms.ST_NEIGHBORS).to_json('data'),
                            ms.ST_JOINED: ms.get_state_elem(ms.ST_JOINED).to_json('data'),
                        }
                    self.viewer.spc.renew_mote_state(int(mote, 16), state)
                else:
                    log.warning("Mote {0} not found in mote_states".format(mote))

    # ======================== public ==========================================

    def start_webserver(self, args):
        log.info(
            'Initializing webserver with options: \n\t{0}'.format(
                '\n\t'.join(
                    ['host: {0}'.format(args.host), 'port: {0}'.format(args.port)]
                )
            )
        )

        # ===== add a web interface
        web_server = bottle.Bottle()
        WebServer(self.app, web_server)

        # start web interface in a separate thread
        webthread = threading.Thread(
            target=web_server.run,
            kwargs={
                'host': args.host,
                'port': args.port,
                'quiet': not self.debug,
                'debug': self.debug,
            }
        )
        webthread.start()

    # ======================== commands =========================================

    def do_state(self, arg):
        """
        Prints provided state, or lists states.
        Usage: state [state-name]
        """
        if not arg:
            for ms in self.app.mote_states:
                output = []
                output += ['Available states:']
                output += [' - {0}'.format(s) for s in ms.get_state_elem_names()]
                log.info('\n'.join(output))
        else:
            for ms in self.app.mote_states:
                try:
                    log.info(str(ms.get_state_elem(arg)))
                except ValueError as err:
                    log.error(err)

    def do_list(self, arg):
        """List available states. (Obsolete; use 'state' without parameters.)"""
        self.do_state('')

    def do_root(self, arg):
        """
        Sets dagroot to the provided mote, or lists motes
        Usage: root [serial-port]
        """

        if not arg:
            log.info('Available ports:')
            if self.app.mote_states:
                for ms in self.app.mote_states:
                    log.info('MOTE ID: {0}'.format(ms.mote_connector.serialport))
            else:
                log.warning('No motes available. Did you attach the hardware or specify the number of simMotes?')
        else:
            for ms in self.app.mote_states:
                try:
                    if ms.mote_connector.serialport == arg:
                        ms.trigger_action(MoteState.TRIGGER_DAGROOT)
                except ValueError as err:
                    log.error(err)
        return False

    def do_set(self, arg):
        """
        Sets mote with parameters
        Usag
        """
        if not arg:
            log.info('Available ports:')
            if self.app.mote_states:
                for ms in self.app.mote_states:
                    log.info('{0}'.format(ms.mote_connector.serialport))
            else:
                log.warning('No motes available. Did you attach the hardware or specify the number of simMotes?')
        else:
            try:
                [port, command, parameter] = arg.split(' ')
                for ms in self.app.mote_states:
                    try:
                        if ms.mote_connector.serialport == port:
                            ms.trigger_action([MoteState.SET_COMMAND, command, parameter])
                    except ValueError as err:
                        log.error(err)
            except ValueError as err:
                log.error(err)

    def help_all(self):
        """ Lists first line of help for all documented commands """

        names = self.get_names()
        names.sort()
        maxlen = 65
        log.info('type "help <topic>" for topic details\n'.format(80 - maxlen - 3))
        for name in names:
            if name[:3] == 'do_':
                try:
                    doc = getattr(self, name).__doc__
                    if doc:
                        # Handle multi-line doc comments and format for length.
                        doclines = doc.splitlines()
                        doc = doclines[0]
                        if len(doc) == 0 and len(doclines) > 0:
                            doc = doclines[1].strip()
                        if len(doc) > maxlen:
                            doc = doc[:maxlen] + '...'
                        log.info('{0} - {1}\n'.format(name[3:80 - maxlen], doc))
                except AttributeError:
                    pass

    def do_quit(self, arg):
        self.quit = True
        self.t.join()

        self.app.close()
        return True

    def default(self, args):
        pass

    def postcmd(self, stop, args):
        self.viewer.repl.panels[0].repl.render_panel()
        return stop

    def emptyline(self):
        return


# ============================ main ============================================
DEFAULT_MOTE_COUNT = 3


def _add_parser_args(parser):
    """ Adds arguments specific to web UI. """
    parser.add_argument(
        '--web',
        dest='web',
        default=False,
        action='store_true',
        help='start a webserver that provides a control panel to OpenVisualizer'
    )

    parser.add_argument(
        '-s', '--sim',
        dest='simulator_mode',
        default=False,
        action='store_true',
        help='simulation mode, with default of {0} motes'.format(DEFAULT_MOTE_COUNT)
    )

    parser.add_argument(
        '-n', '--simCount',
        dest='num_motes',
        type=int,
        default=0,
        help='simulation mode, with provided mote count'
    )

    parser.add_argument(
        '-t', '--trace',
        dest='trace',
        default=False,
        action='store_true',
        help='enables memory debugging'
    )

    parser.add_argument(
        '-o', '--simTopology',
        dest='sim_topology',
        default='',
        action='store',
        help='force a certain toplogy (simulation mode only)'
    )

    parser.add_argument(
        '-d', '--debug',
        dest='debug',
        default=False,
        action='store_true',
        help='enables application debugging'
    )

    parser.add_argument(
        '-z', '--usePageZero',
        dest='use_page_zero',
        default=False,
        action='store_true',
        help='use page number 0 in page dispatch (only works with one-hop)'
    )

    parser.add_argument(
        '-i', '--iotlabMotes',
        dest='iotlab_motes',
        default='',
        action='store',
        help='comma-separated list of IoT-LAB motes (e.g. "wsn430-9,wsn430-34,wsn430-3")'
    )

    parser.add_argument(
        '-b', '--opentestbed',
        dest='testbed_motes',
        default=False,
        action='store_true',
        help='connect motes from opentestbed'
    )

    parser.add_argument(
        '--mqtt-broker-address',
        dest='mqtt_broker_address',
        default='argus.paris.inria.fr',
        action='store',
        help='MQTT broker address to use'
    )

    parser.add_argument(
        '--opentun-null',
        dest='opentun_null',
        default=False,
        action='store_true',
        help='don\'t use TUN device'
    )

    parser.add_argument(
        '-p', '--pathTopo',
        dest='path_topo',
        default='',
        action='store',
        help='a topology can be loaded from a json file'
    )

    parser.add_argument(
        '-r', '--root',
        dest='root',
        default='',
        action='store',
        help='set mote associated to serial port as root'
    )
    parser.add_argument(
        '-H',
        '--host',
        dest='host',
        default='0.0.0.0',
        action='store',
        help='host address'
    )

    parser.add_argument(
        '-P',
        '--port',
        dest='port',
        default=8080,
        action='store',
        help='port number'
    )

    parser.add_argument(
        '-a', '--appDir',
        dest='appdir',
        default='.',
        action='store',
        help='working directory'
    )


def main(stdscr):
    # detect mouse clicks
    curses.mousemask(-1)
    curses.mouseinterval(200)

    parser = ArgumentParser()
    _add_parser_args(parser)

    args = parser.parse_args()

    conf_dir, data_dir, log_dir = u.init_external_dirs(args.appdir, args.debug)

    # Must use a '/'-separated path for log dir, even on Windows.
    logging.config.fileConfig(os.path.join(conf_dir, 'logging.conf'),
                              {'logDir': u.force_slash_sep(log_dir, args.debug)})

    # prepare curses terminal
    viewer = TermViewer(stdscr)

    # provide the curses logging handler with a pawin object
    for handler in log.handlers:
        if isinstance(handler, LogDispatcher):
            handler.viewer = viewer

    # initialize openvisualizer application
    app = openvisualizer_app.main(parser, conf_dir, data_dir, log_dir, DEFAULT_MOTE_COUNT)

    cli = Cli(app, viewer)
    cli.discover_motes()

    log.info('Using external dirs:\n    {}'.format(
        '\n    '.join(['conf     = {0}'.format(conf_dir),
                       'data     = {0}'.format(data_dir),
                       'log      = {0}'.format(log_dir)],
                      )))

    # start web server
    cli.start_webserver(args)

    f_quit = False
    cli.input_box = viewer.repl.panels[0].text_box
    while not f_quit:
        user_input = cli.input_box.edit(cli.validator)
        f_quit = cli.onecmd(user_input.strip())
        f_quit = cli.postcmd(f_quit, user_input)


if __name__ == "__main__":
    curses.wrapper(main)
    os.kill(os.getpid(), signal.SIGTERM)
