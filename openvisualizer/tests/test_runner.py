#!/usr/bin/env python
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


if __name__ == '__main__':
    parser = ArgumentParser()
    _add_parser_args(parser)
    arg_space = parser.parse_known_args()[0]


    pytest.main(['-x', 'software'])
