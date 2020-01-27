import logging.handlers

import pytest
from scapy.compat import raw
from scapy.layers.inet6 import IPv6, ICMPv6EchoRequest

from tun import TunInterface

# ============================ logging =========================================
LOGFILE_NAME = 'test_ping.log'

log = logging.getLogger('test_ping')
log.setLevel(logging.ERROR)
log.addHandler(logging.NullHandler())

logHandler = logging.handlers.RotatingFileHandler(LOGFILE_NAME, backupCount=5, mode='w')
logHandler.setFormatter(logging.Formatter("%(asctime)s [%(name)s:%(levelname)s] %(message)s"))

for loggerName in ['test_ping']:
    temp = logging.getLogger(loggerName)
    temp.setLevel(logging.DEBUG)
    temp.addHandler(logHandler)


@pytest.fixture(scope="session")
def etun():
    return TunInterface()


# ============================ defines =========================================

DEST_NETWORK_PREFIX = "bbbb::"


# ============================ tests ===========================================

def test_ex_ping_request(etun):
    """
    Injects a ping request that originates from an external network
    """
    ip = IPv6(src=etun.ipv6_prefix + "::0002", dst=DEST_NETWORK_PREFIX + "1415:92cc:0:2", hlim=64)
    icmp = ICMPv6EchoRequest()

    pkt = ip / icmp

    etun.write(list(bytearray(raw(pkt))))
