from random import randint

import pytest
from scapy.compat import raw
from scapy.layers.inet6 import IPv6, ICMPv6EchoRequest, ICMPv6EchoReply

from openvisualizer.moteConnector import OpenParser
from openvisualizer.openLbr.sixlowpan_frag import Fragmentor
from openvisualizer.tests.firmware.conftest import is_my_icmpv6


# =========================== defines ==========================================

# =========================== helpers ==========================================


def _read_joined_addresses():
    with open('node_addresses.txt', 'r') as f:
        addresses = [line.rstrip() for line in f]
    return addresses


def pytest_generate_tests(metafunc):
    if "node_addr" in metafunc.fixturenames:
        metafunc.parametrize("node_addr", _read_joined_addresses())


# ============================ tests ===========================================

@pytest.mark.parametrize("payload_len", range(100, 1200, 100))
def test_basic_6lo_fragmentation(etun, ov_env, my_addr, node_addr, payload_len):
    """
    Test basic 6LoWPAN fragmentation and reassembly functions
    """
    _, node_joined = ov_env
    if node_addr not in node_joined:
        pytest.skip("Node with address {} never joined, skipping this test".format(node_addr))

    ip = IPv6(src=my_addr, dst=node_addr, hlim=64)
    id = randint(0, 65535)
    seq = randint(0, 65535)
    icmp = ICMPv6EchoRequest(id=id, seq=seq)
    pkt = ip / icmp

    payload = "".join([chr(randint(0, 255)) for b in range(payload_len)])
    pkt.add_payload(payload)

    etun.write(list(bytearray(raw(pkt))))
    received = etun.read(dest=my_addr, timeout=25)

    timeout = True
    for recv_pkt in received:
        ipv6_pkt = IPv6(recv_pkt)
        if is_my_icmpv6(ipv6_pkt, node_addr, my_addr):
            timeout = False
            icmp = ICMPv6EchoReply(raw(ipv6_pkt)[40:])
            # check if icmp headers match
            assert icmp.id == id
            assert icmp.seq == seq

    if timeout:
        # node to failed to respond with an ICMPv6 echo before timeout
        pytest.fail("Timeout on ICMPv6 Echo Response!")


@pytest.mark.sim_only
def test_cleanup_on_fragment_loss(etun, ov_env, my_addr, node_addr):
    """
    Test the cleanup function after a fragment loss
    """

    pass
