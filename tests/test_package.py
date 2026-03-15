from __future__ import annotations

from argparse import ArgumentParser

from capn_crunch import BaseOptions, add_options_to_parser


class ShipOptions(BaseOptions):
    ship: str = "Black Pearl"


def test_options():
    ship_options = ShipOptions()
    ship_options.with_options(ship="Interceptor")


def test_parser():
    parser = ArgumentParser()
    ship_parser = add_options_to_parser(parser=parser, options_class=ShipOptions)
    args = ship_parser.parse_args()

    assert args.ship == "Black Pearl"
