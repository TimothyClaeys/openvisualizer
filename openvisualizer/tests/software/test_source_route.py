#!/usr/bin/env python

import json
import logging
import logging.handlers

import pytest

import openvisualizer.openvisualizer_utils as u
from openvisualizer.RPL import SourceRoute, topology

# ============================ logging =========================================

LOGFILE_NAME = 'test_sourceroute.log'

log = logging.getLogger('test_sourceroute')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

logHandler = logging.handlers.RotatingFileHandler(LOGFILE_NAME, backupCount=5, mode='w')
logHandler.setFormatter(logging.Formatter("%(asctime)s [%(name)s:%(levelname)s] %(message)s"))

for loggerName in ['test_sourceRoute', 'SourceRoute']:
    temp = logging.getLogger(loggerName)
    temp.setLevel(logging.DEBUG)
    temp.addHandler(logHandler)

# ============================ defines =========================================

MOTE_A = [0xaa] * 8
MOTE_B = [0xbb] * 8
MOTE_C = [0xcc] * 8
MOTE_D = [0xdd] * 8

# ============================ fixtures ========================================

EXPECTED_SOURCE_ROUTE = [
    json.dumps((MOTE_B, [MOTE_B, MOTE_A])),
    json.dumps((MOTE_C, [MOTE_C, MOTE_B, MOTE_A])),
    json.dumps((MOTE_D, [MOTE_D, MOTE_C, MOTE_B, MOTE_A])),
]


@pytest.fixture(params=EXPECTED_SOURCE_ROUTE)
def expected_source_route(request):
    return request.param


# ============================ helpers =========================================

# ============================ tests ===========================================

def test_source_route(expected_source_route):
    '''
    This tests the following topology
    
    MOTE_A <- MOTE_B <- MOTE_C <- MOTE_D
    '''

    source_route = SourceRoute.SourceRoute()

    # instantiate topology module (otherwise the dispatch calls will fail)
    _ = topology.topology()

    source_route.dispatch(
        signal='updateParents',
        data=(tuple(MOTE_B), [MOTE_A]),
    )
    source_route.dispatch(
        signal='updateParents',
        data=(tuple(MOTE_C), [MOTE_B]),
    )
    source_route.dispatch(
        signal='updateParents',
        data=(tuple(MOTE_D), [MOTE_C]),
    )

    expected_destination = json.loads(expected_source_route)[0]
    expected_route = json.loads(expected_source_route)[1]
    calculated_route = source_route.getSourceRoute(expected_destination)

    # log
    if log.isEnabledFor(logging.DEBUG):
        output = []
        output += ['\n']
        output += ['expected_destination: {0}'.format(u.formatAddr(expected_destination))]
        output += ['expected_route:']
        for m in expected_route:
            output += ['- {0}'.format(u.formatAddr(m))]
        output += ['calculated_route:']
        for m in calculated_route:
            output += ['- {0}'.format(u.formatAddr(m))]
        output = '\n'.join(output)
        log.debug(output)

    assert calculated_route == expected_route