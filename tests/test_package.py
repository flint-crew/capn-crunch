from __future__ import annotations

from argparse import ArgumentParser, BooleanOptionalAction
from pathlib import Path
from typing import Literal, Optional

import pytest
from pydantic.fields import FieldInfo

from capn_crunch import BaseOptions, add_options_to_parser, create_options_from_parser
from capn_crunch.core import BooleanFlagPair, _create_argparse_options


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


class SailOptions(BaseOptions):
    hoist: bool = False
    """Hoist the sails"""
    anchor: bool = True
    """Drop the anchor"""


class ReefOptions(BaseOptions):
    no_reef: bool = False
    """Avoid the reef"""


class MutinyOptions(BaseOptions):
    mutiny: bool
    """Whether the crew mutinies"""


def test_bool_argparse_options():
    field = FieldInfo(default=True, annotation=bool, description="Drop the anchor")
    field_name, field_options = _create_argparse_options(name="drop_anchor", field=field)
    assert field_name == "--drop-anchor"
    assert field_options["action"] is BooleanFlagPair
    assert field_options["default"] is True


def test_parser_bool_flags():
    """Every bool is a --name / --no-name pair, whatever its default"""
    parser = add_options_to_parser(parser=ArgumentParser(), options_class=SailOptions)

    options = create_options_from_parser(parser.parse_args([]), SailOptions)
    assert options.hoist is False
    assert options.anchor is True

    args = parser.parse_args(["--hoist", "--no-anchor"])
    options = create_options_from_parser(args, SailOptions)
    assert options.hoist is True
    assert options.anchor is False

    args = parser.parse_args(["--no-hoist", "--anchor"])
    options = create_options_from_parser(args, SailOptions)
    assert options.hoist is False
    assert options.anchor is True


def test_parser_required_bool():
    parser = add_options_to_parser(parser=ArgumentParser(), options_class=MutinyOptions)

    assert parser.parse_args(["--mutiny"]).mutiny is True
    assert parser.parse_args(["--no-mutiny"]).mutiny is False
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_parser_bool_named_no():
    """A bool named no_* pairs --no-name with --name, not --no-no-name"""
    parser = add_options_to_parser(parser=ArgumentParser(), options_class=ReefOptions)

    assert parser.parse_args([]).no_reef is False
    assert parser.parse_args(["--no-reef"]).no_reef is True
    assert parser.parse_args(["--reef"]).no_reef is False
    with pytest.raises(SystemExit):
        parser.parse_args(["--no-no-reef"])
    assert "[--no-reef | --reef]" in parser.format_usage()


def test_bool_flags_are_boolean_optional_actions():
    """Tools such as configargparse recognise BooleanOptionalAction and expect
    each flag to be followed by its negation"""
    parser = add_options_to_parser(parser=ArgumentParser(), options_class=ReefOptions)
    (action,) = [a for a in parser._actions if a.dest == "no_reef"]

    assert isinstance(action, BooleanOptionalAction)
    assert action.option_strings == ["--no-reef", "--reef"]
