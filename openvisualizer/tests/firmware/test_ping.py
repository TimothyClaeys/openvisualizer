from random import randint

import pytest
from scapy.compat import raw
from scapy.layers.inet6 import IPv6, ICMPv6EchoRequest, ICMPv6EchoReply

from openvisualizer.tests.firmware.conftest import is_my_icmpv6


# =========================== defines ==========================================

# =========================== fixtures =========================================

# =========================== helpers ==========================================


def _read_joined_addresses():
    with open('node_addresses.txt', 'r') as f:
        addresses = [line.rstrip() for line in f]
    return addresses


def pytest_generate_tests(metafunc):
    if "node_addr" in metafunc.fixturenames:
        metafunc.parametrize("node_addr", _read_joined_addresses())


# ============================ tests ===========================================

def test_ex_ping_request(etun, my_addr, node_addr, ov_env):
    """
    Injects a ping request that originates from an external network
    """
    _, nodes_joined = ov_env
    if node_addr not in nodes_joined:
        pytest.skip("Node with address {} never joined, skipping this test".format(node_addr))

    ip = IPv6(src=my_addr, dst=node_addr, hlim=64)
    id = randint(0, 65535)
    seq = randint(0, 65535)
    icmp = ICMPv6EchoRequest(id=id, seq=seq)
    pkt = ip / icmp
    etun.write(list(bytearray(raw(pkt))))
    received = etun.read(dest=my_addr, timeout=5)

    timeout = True
    for pkt in received:
        ipv6_pkt = IPv6(pkt)
        if is_my_icmpv6(ipv6_pkt, node_addr, my_addr):
            timeout = False
            icmp = ICMPv6EchoReply(raw(ipv6_pkt)[40:])
            # check if icmp headers match
            assert icmp.id == id
            assert icmp.seq == seq

    if timeout:
        # node failed to respond with an ICMPv6 echo before timeout
        pytest.fail("Timeout on ICMPv6 Echo Response!")
