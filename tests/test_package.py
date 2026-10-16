from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from typing import Literal, Optional

import pytest
from pydantic.fields import FieldInfo

from capn_crunch import BaseOptions, add_options_to_parser, create_options_from_parser
from capn_crunch.core import _create_argparse_options


class ShipOptions(BaseOptions):
    ship: str = "Black Pearl"


class CrewOptions(BaseOptions):
    cube_products: list[Literal["dirty", "clean", "model"]] = []
    """Which cubes to write"""
    mode: Literal["fast", "slow"] = "fast"
    """The sailing mode"""
    level: Literal[1, 2, 3] = 1
    """The crew level"""


def test_options():
    ship_options = ShipOptions()
    ship_options.with_options(ship="Interceptor")


def test_parser():
    parser = ArgumentParser()
    ship_parser = add_options_to_parser(parser=parser, options_class=ShipOptions)
    args = ship_parser.parse_args([])

    assert args.ship == "Black Pearl"


def test_fieldinfo_to_argparse_options():
    """The pydantic ``FieldInfo`` object is used to generate the options that would be
    splat into an ArgumentParser.add_argument method. Ensure the expected mappings from
    types to argument options make sense"""
    field = FieldInfo(default=1, annotation=int, description="An example description")
    field_name, field_options = _create_argparse_options(name="jack_sparrow", field=field)
    assert field_name == "--jack-sparrow"
    assert field_options["action"] == "store"
    assert field_options["default"] == 1
    assert field_options["help"] == "An example description"

    field = FieldInfo(annotation=int, description="An example description")
    field_name, field_options = _create_argparse_options(name="jack_sparrow", field=field)
    assert field_name == "jack_sparrow"
    assert field_options["action"] == "store"
    assert field_options["help"] == "An example description"

    field = FieldInfo(
        default=[1, 2, 3, 4], annotation=list[int], description="An example description"
    )
    field_name, field_options = _create_argparse_options(name="jack_sparrow", field=field)
    assert field_name == "--jack-sparrow"
    assert field_options["action"] == "store"
    assert field_options["default"] == [1, 2, 3, 4]
    assert field_options["help"] == "An example description"
    assert field_options["nargs"] == "+"

    field = FieldInfo(
        default=("foo", "bar", 3),
        annotation=tuple[str, str, int],
    )
    field_name, field_options = _create_argparse_options(name="jack_sparrow", field=field)
    assert field_options["default"] == ("foo", "bar", 3)
    assert field_options["nargs"] == 3

    field = FieldInfo(
        default=("foo", "bar"),
        annotation=tuple[str, ...],
    )
    field_name, field_options = _create_argparse_options(name="jack_sparrow", field=field)
    assert field_options["default"] == (
        "foo",
        "bar",
    )
    assert field_options["nargs"] == "+"

    field = FieldInfo(
        default=None,
        annotation=tuple[str, str] | None,
    )
    field_name, field_options = _create_argparse_options(name="jack_sparrow", field=field)
    assert field_options["default"] == None  # noqa E711
    assert field_options["nargs"] == 2


def test_optional_container_nargs():
    """Containers in a union with ``None`` should keep the right nargs"""
    field = FieldInfo(default=None, annotation=list[int] | None)
    _, field_options = _create_argparse_options(name="jack_sparrow", field=field)
    assert field_options["nargs"] == "+"

    field = FieldInfo(default=None, annotation=set[str] | None)
    _, field_options = _create_argparse_options(name="jack_sparrow", field=field)
    assert field_options["nargs"] == "+"

    field = FieldInfo(default=None, annotation=Optional[tuple[str, str]])
    _, field_options = _create_argparse_options(name="jack_sparrow", field=field)
    assert field_options["nargs"] == 2


def test_literal_choices_argparse_options():
    """``Literal`` annotations should set the argparse choices"""
    field = FieldInfo(default="a", annotation=Literal["a", "b"])
    _, field_options = _create_argparse_options(name="jack_sparrow", field=field)
    assert field_options["choices"] == ("a", "b")
    assert "nargs" not in field_options
    assert "type" not in field_options

    field = FieldInfo(default=[], annotation=list[Literal["dirty", "clean", "model"]])
    _, field_options = _create_argparse_options(name="jack_sparrow", field=field)
    assert field_options["choices"] == ("dirty", "clean", "model")
    assert field_options["nargs"] == "+"

    field = FieldInfo(default=("x",), annotation=tuple[Literal["x", "y"], ...])
    _, field_options = _create_argparse_options(name="jack_sparrow", field=field)
    assert field_options["choices"] == ("x", "y")
    assert field_options["nargs"] == "+"

    field = FieldInfo(default=None, annotation=Literal["a", "b"] | None)
    _, field_options = _create_argparse_options(name="jack_sparrow", field=field)
    assert field_options["choices"] == ("a", "b")
    assert "nargs" not in field_options

    field = FieldInfo(default=None, annotation=list[Literal["dirty", "clean"]] | None)
    _, field_options = _create_argparse_options(name="jack_sparrow", field=field)
    assert field_options["choices"] == ("dirty", "clean")
    assert field_options["nargs"] == "+"

    field = FieldInfo(default="a", annotation=Literal["a"] | Literal["b", "a"])
    _, field_options = _create_argparse_options(name="jack_sparrow", field=field)
    assert field_options["choices"] == ("a", "b")

    field = FieldInfo(default=1, annotation=Literal[1, 2, 3])
    _, field_options = _create_argparse_options(name="jack_sparrow", field=field)
    assert field_options["choices"] == (1, 2, 3)
    assert field_options["type"] is int

    # Literals that argparse can not convert to are left to pydantic
    for annotation in (Literal[True, False], Literal["auto", 1], Literal["a"] | int):
        field = FieldInfo(default="a", annotation=annotation)
        _, field_options = _create_argparse_options(name="jack_sparrow", field=field)
        assert "choices" not in field_options
        assert "type" not in field_options


def test_parser_literal_choices():
    """Choices should be enforced by the parser and survive conversion to options"""
    parser = add_options_to_parser(parser=ArgumentParser(), options_class=CrewOptions)

    help_text = parser.format_help()
    assert "{dirty,clean,model}" in help_text
    assert "{fast,slow}" in help_text

    args = parser.parse_args(["--cube-products", "dirty", "clean", "--level", "2"])
    crew_options = create_options_from_parser(args, CrewOptions)
    assert crew_options.cube_products == ["dirty", "clean"]
    assert crew_options.mode == "fast"
    assert crew_options.level == 2

    with pytest.raises(SystemExit):
        parser.parse_args(["--cube-products", "dirty", "bad"])

    with pytest.raises(SystemExit):
        parser.parse_args(["--level", "4"])
