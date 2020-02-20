#!/usr/bin/env python
import os
from argparse import ArgumentParser

import pytest


def _add_parser_args(parser):
    """Adds arguments specific to the unittests"""

    parser.add_argument(
        '--target',
        dest='target_code',
        default='',
        action='store',
        help='specify code to test'
    )

    parser.add_argument(
        '--simCount',
        dest='simcount',
        default='0',
        action='store',
        help='number of motes to simulate'
    )

    parser.add_argument(
        '--nftimeout',
        dest='nftimeout',
        default='60',
        action='store',
        help='timeout on network formation'
    )


class TestRunner:
    BASE_SIM_IPV6_ADDR = "bbbb:0:0:0:1415:92cc:0:"

    def __init__(self, directory, simulation, nftimeout):
        self.directory = directory
        self.simulation = int(simulation)
        self.nftimeout = int(nftimeout)
        self.path = os.path.abspath(os.getcwd())

    def run_tests(self):
        test_path = os.path.join(self.path, self.directory)
        args = self._create_pytest_command(test_path)
        pytest.main(args)

    def _create_pytest_command(self, test_path):
        base_args = ['-x', test_path, '-v', '-rA', '--maxfail=1']

        if self.directory == "firmware":
            if self.simulation > 0:
                base_args.append('--simCount=' + str(self.simulation))

                with open("node_addresses.txt", 'w') as f:
                    for addr in range(2, self.simulation + 1):
                        f.write(self.BASE_SIM_IPV6_ADDR + str(addr) + '\n')

            else:
                try:
                    f = open("node_addresses.txt")
                except IOError:
                    raise SystemExit
                finally:
                    f.close()

            base_args.append('--nftimeout=' + str(self.nftimeout))

        return base_args


if __name__ == '__main__':
    parser = ArgumentParser()
    _add_parser_args(parser)
    arg_space = parser.parse_known_args()[0]

    tr = TestRunner(directory=arg_space.target_code, simulation=arg_space.simcount, nftimeout=arg_space.nftimeout)
    tr.run_tests()
