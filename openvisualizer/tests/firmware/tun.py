import os
import select
import struct
from fcntl import ioctl

from scapy.layers.inet6 import IPv6
from scapy.packet import Packet


def is_ipv6(data):
    return (data[0] & 0xf0) == 0x61


class TunInterface:
    VIRTUAL_TUN_ID = [0x00, 0x00, 0x86, 0xdd]

    IFF_TUN = 0x0001
    TUN_SET_IFF = 0x400454ca
    ETHERNET_MTU = 1500

    def __init__(self, prefix='cccc:0000:0000:0000', host='0000:0000:0000:0001'):
        self.ipv6_prefix = prefix
        self.ipv6_host = host
        self.tun_iff = self._create_tun_if()

    def _create_tun_if(self):
        return_val = os.open("/dev/net/tun", os.O_RDWR)
        ifs = ioctl(return_val, self.TUN_SET_IFF, struct.pack("16sH", "tun%d", self.IFF_TUN))
        self.if_name = ifs.decode('UTF-8')[:16].strip("\x00")

        os.system('ip tuntap add dev ' + self.if_name + ' mode tun user root')
        os.system('ip link set ' + self.if_name + ' up')
        os.system('ip -6 addr add ' + self.ipv6_prefix + ':' + self.ipv6_host + '/64 dev ' + self.if_name)
        os.system('ip -6 addr add fe80::' + self.ipv6_host + '/64 dev ' + self.if_name)

        return return_val

    def write(self, data):
        if not self.tun_iff:
            return

        # add tun header and convert to bytes
        data = self.VIRTUAL_TUN_ID + data
        data = "".join([chr(b) for b in data])

        try:
            # write over tuntap interface
            os.write(self.tun_iff, data)
        except Exception as err:
            print("write failed")
