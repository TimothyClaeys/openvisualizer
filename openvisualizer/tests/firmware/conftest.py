import logging.handlers
import os
import re
import threading
import time
from Queue import Queue, Empty
from random import randint
from subprocess import Popen, PIPE

import pytest
from ipaddr import IPv6Address

from openvisualizer.tests.firmware.tun import TunInterface

LOGFILE_NAME = 'test_firmware.log'

log = logging.getLogger('test_firmware')
log.setLevel(logging.INFO)
log.addHandler(logging.NullHandler())

logHandler = logging.handlers.RotatingFileHandler(LOGFILE_NAME, backupCount=5, mode='w')
logHandler.setFormatter(logging.Formatter("%(asctime)s [%(name)s:%(levelname)s] %(message)s"))

for loggerName in ['test_firmware']:
    temp = logging.getLogger(loggerName)
    temp.setLevel(logging.DEBUG)
    temp.addHandler(logHandler)

file_openwsn = "openwsn.txt"

# ============================= defines =======================================

NH_ICMPV6 = 58


# ============================= helpers =======================================

def pytest_configure(config):
    config.addinivalue_line("markers", "sim_only: mark test as simulation only to run")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--simCount") > 0:
        # --simCount not 0 in cli: run all tests
        return
    skip_real_hardware = pytest.mark.skip(reason="need --simCount option to run")
    for item in items:
        if "sim_only" in item.keywords:
            item.add_marker(skip_real_hardware)


def pytest_addoption(parser):
    parser.addoption("--simCount", action="store", default=0)
    parser.addoption("--nftimeout", action="store", default=60)


def stdout_reader(proc, outq):
    for line in iter(proc.stdout.readline, b''):
        outq.put(line.decode('utf-8'))
        with open(file_openwsn, 'a') as f:
            f.write(line.decode('utf-8'))


def stderr_reader(proc, outq):
    for line in iter(proc.stderr.readline, b''):
        outq.put(line.decode('utf-8'))
        with open(file_openwsn, 'a') as f:
            f.write(line.decode('utf-8'))


def is_my_icmpv6(ipv6_pkt, his_address, my_address):
    if IPv6Address(ipv6_pkt.src).exploded == IPv6Address(his_address).exploded and \
            IPv6Address(ipv6_pkt.dst).exploded == IPv6Address(my_address).exploded and \
            ipv6_pkt.nh == NH_ICMPV6:
        return True
    else:
        return False


# ============================ fixtures =======================================

@pytest.fixture(scope="session", autouse=True)
def ov_env(request):
    log.info("Setting up the network for testing...")

    os.chdir("../../")

    arguments = ["scons", "runweb"]

    simulated_motes = int(request.config.getoption("--simCount"))
    if simulated_motes > 0:
        log.info(" --> Running in simulation mode with {} motes".format(simulated_motes))
        arguments.extend(["--simCount=" + str(simulated_motes), "--simTopology=linear"])
    else:
        log.info(" --> Running in hardware mode")

    proc = Popen(arguments, stderr=PIPE, stdin=PIPE, stdout=PIPE, shell=False)

    outq = Queue()

    readers = [threading.Thread(target=stdout_reader, args=(proc, outq)),
               threading.Thread(target=stderr_reader, args=(proc, outq))]
    map(lambda r: r.start(), readers)

    # contains all the unique addresses of the nodes in the network
    node_set = set()

    proc.stdin.write(b'root emulated1\n')
    proc.stdin.flush()

    nftimeout = int(request.config.getoption("--nftimeout"))
    timeout = time.time() + nftimeout
    log.info(" --> Network formation timeout {}s".format(nftimeout))

    if simulated_motes > 0:
        log.info("Waiting for motes to join... ({}/{})".format(len(node_set), simulated_motes - 1))
    while time.time() < timeout:
        try:
            line = outq.get(block=False)
            m = re.search('received RPL DAO from (([0-9a-f]{1,4}:+){1,7}[0-9a-f]{1,4})', line)
            if m:
                prv_len = len(node_set)
                address = m.group(1)
                node_set.add(address)
                curr_len = len(node_set)
                if simulated_motes > 0 and prv_len != curr_len:
                    log.info("Waiting for motes to join... ({}/{})".format(len(node_set), simulated_motes - 1))
                    if simulated_motes > 0 and len(node_set) >= simulated_motes - 1:
                        break
        except Empty:
            pass

    if simulated_motes > 0 and len(node_set) < simulated_motes - 1:
        log.warning("Timeout on network formation.")
        log.warning("Continuing with the joined motes.")
    else:
        log.info("All motes joined")

    for addr in node_set:
        log.info("Found {}".format(addr))

    yield proc, node_set

    # clean up openvisualizer environment after tests go out of scope
    proc.stdin.write(b'quit\n')
    proc.stdin.flush()

    map(lambda r: r.join(), readers)


@pytest.fixture(scope="session")
def etun():
    return TunInterface()


@pytest.fixture(scope="module")
def my_addr(etun):
    return etun.ipv6_prefix + hex(randint(2, 65535))[2:]
