from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

from pydantic.fields import FieldInfo

from capn_crunch import BaseOptions, add_options_to_parser
from capn_crunch.core import _create_argparse_options


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


def test_fieldinfo_to_argparse_options():
    """The pydantic ``FieldInfo`` object is used to generate the options that would be
    splat into an ArgumentParser.add_argument method. Ensure the expected mappings from
    types to argument options make sense"""
    field = FieldInfo(default=1, annotation=int, description="An example description")
    field_name, field_options = _create_argparse_options(
        name="jack_sparrow", field=field
    )
    assert field_name == "--jack-sparrow"
    assert field_options["action"] == "store"
    assert field_options["default"] == 1
    assert field_options["help"] == "An example description"

    field = FieldInfo(annotation=int, description="An example description")
    field_name, field_options = _create_argparse_options(
        name="jack_sparrow", field=field
    )
    assert field_name == "jack_sparrow"
    assert field_options["action"] == "store"
    assert field_options["help"] == "An example description"

    field = FieldInfo(
        default=[1, 2, 3, 4], annotation=list[int], description="An example description"
    )
    field_name, field_options = _create_argparse_options(
        name="jack_sparrow", field=field
    )
    assert field_name == "--jack-sparrow"
    assert field_options["action"] == "store"
    assert field_options["default"] == [1, 2, 3, 4]
    assert field_options["help"] == "An example description"
    assert field_options["nargs"] == "+"

    field = FieldInfo(
        default=("foo", "bar", 3),
        annotation=tuple[str, str, int],
    )
    field_name, field_options = _create_argparse_options(
        name="jack_sparrow", field=field
    )
    assert field_options["default"] == ("foo", "bar", 3)
    assert field_options["nargs"] == 3

    field = FieldInfo(
        default=("foo", "bar"),
        annotation=tuple[str, ...],
    )
    field_name, field_options = _create_argparse_options(
        name="jack_sparrow", field=field
    )
    assert field_options["default"] == (
        "foo",
        "bar",
    )
    assert field_options["nargs"] == "+"

    field = FieldInfo(
        default=None,
        annotation=tuple[str, str] | None,
    )
    field_name, field_options = _create_argparse_options(
        name="jack_sparrow", field=field
    )
    assert field_options["default"] == None  # noqa E711
    assert field_options["nargs"] == 2
