from random import randint

import pytest
from scapy.compat import raw
from scapy.layers.inet6 import IPv6, ICMPv6EchoRequest, ICMPv6EchoReply

from openvisualizer.tests.firmware.conftest import is_my_icmpv6

# =========================== defines ==========================================

ROUND_TRIP_TIMEOUT = 60
IPV6_HDR_LEN = 40


# =========================== helpers ==========================================

def generate_icmpv6_pkt(src, dst, payload_length):
    ip = IPv6(src=src, dst=dst, hlim=64)
    id = randint(0, 65535)
    seq = randint(0, 65535)
    icmp = ICMPv6EchoRequest(id=id, seq=seq)
    pkt = ip / icmp

    payload = "".join([chr(randint(0, 255)) for b in range(payload_length)])
    pkt.add_payload(payload)

    return id, seq, list(bytearray(raw(pkt)))


def _read_joined_addresses():
    with open('node_addresses.txt', 'r') as f:
        addresses = [line.rstrip() for line in f]
    return addresses


def pytest_generate_tests(metafunc):
    if "node_addr" in metafunc.fixturenames:
        metafunc.parametrize("node_addr", _read_joined_addresses())


# ============================ tests ===========================================

@pytest.mark.parametrize("payload_len", range(100, 1000, 100))
def test_basic_6lo_fragmentation(etun, ov_env, my_addr, node_addr, payload_len):
    """
    Test basic 6LoWPAN fragmentation and reassembly functions
    """
    _, node_joined = ov_env
    if node_addr not in node_joined:
        pytest.skip("Node with address {} never joined, skipping this test".format(node_addr))

    id, seq, pkt = generate_icmpv6_pkt(my_addr, node_addr, payload_len)
    etun.write(pkt)
    received = etun.read(dest=my_addr, timeout=ROUND_TRIP_TIMEOUT)

    timeout = True
    for recv_pkt in received:
        ipv6_pkt = IPv6(recv_pkt)
        if is_my_icmpv6(ipv6_pkt, node_addr, my_addr):
            timeout = False
            icmp = ICMPv6EchoReply(raw(ipv6_pkt)[IPV6_HDR_LEN:])
            # check if icmp headers match
            assert icmp.id == id
            assert icmp.seq == seq

    if timeout:
        # node to failed to respond with an ICMPv6 echo before timeout
        pytest.fail("Timeout on ICMPv6 Echo Response!")

    # let the network recover between the different tests


@pytest.mark.parametrize("payload_len", range(5, 100, 1))
def test_incremental_payload_6lo_frag(etun, ov_env, my_addr, node_addr, payload_len):
    """
    Test the corner case of the fragmentation code by changing the payload size byte by byte
    """
    _, node_joined = ov_env
    if node_addr not in node_joined:
        pytest.skip("Node with address {} never joined, skipping this test".format(node_addr))

    id, seq, pkt = generate_icmpv6_pkt(my_addr, node_addr, payload_len)
    etun.write(pkt)
    received = etun.read(dest=my_addr, timeout=ROUND_TRIP_TIMEOUT)

    timeout = True
    for recv_pkt in received:
        ipv6_pkt = IPv6(recv_pkt)
        if is_my_icmpv6(ipv6_pkt, node_addr, my_addr):
            timeout = False
            icmp = ICMPv6EchoReply(raw(ipv6_pkt)[IPV6_HDR_LEN:])
            # check if icmp headers match
            assert icmp.id == id
            assert icmp.seq == seq

    if timeout:
        # node to failed to respond with an ICMPv6 echo before timeout
        pytest.fail("Timeout on ICMPv6 Echo Response!")

    # let the network recover between the different tests


@pytest.mark.sim_only
def test_cleanup_on_fragment_loss(etun, ov_env, my_addr, node_addr):
    """
    Test the cleanup function after a fragment loss
    """

    pass
