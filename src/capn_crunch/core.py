"""
Capn-Crunch options.

Contains the core of the option class containers that are used to
hold stateful properties throughout the flint-crew codebases.
"""

from __future__ import annotations

import logging
from types import NoneType, UnionType
from typing import (
    TYPE_CHECKING,
    Any,
    Self,
    TypeVar,
    get_args,
    get_origin,
)

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace

    from pydantic.fields import FieldInfo

logger = logging.getLogger("__name__")


class BaseOptions(BaseModel):
    """
    A base class that Options style flint classes can inherit from.

    This is derived from ``pydantic.BaseModel``,
    and can be used for validation of supplied values.

    Class derived from ``BaseOptions`` are immutable by
    default, and have the docstrings of attributes
    extracted.
    """

    model_config = ConfigDict(
        frozen=True,
        from_attributes=True,
        use_attribute_docstrings=True,
        extra="forbid",
        arbitrary_types_allowed=True,
    )

    def with_options(self, /, **kwargs: dict[str, Any]) -> Self:
        """
        Modify options.

        Returns a new instance of the options class.

        Returns:
            Self: A new instance of the options.

        """
        new_args = self.__dict__.copy()
        new_args.update(**kwargs)

        return self.__class__(**new_args)

    def _asdict(self) -> dict[str, Any]:
        return self.model_dump()


def options_to_dict(input_options: BaseOptions) -> dict:
    """
    Convert options to a dictionary.

    Most of `flint` `Option` and `Result` classes used `typing.NamedTuples`, which carry with
    it a `_asdict` method to convert them to a dictionary. Future roadmap plans to move over to
    pydantic type models. This is a place holder function to help transition to this.

    Args:
        input_options (Any): Item to convert to a dictionary

    Raises:
        TypeError: Raised if the conversion to a dictionary was not successful

    Returns:
        Dict: The dictionary version of the input options

    """
    if "_asdict" in dir(input_options):
        return input_options._asdict()

    try:
        if issubclass(input_options, BaseModel):
            return dict(**input_options.__dict__)
    except TypeError:
        logger.debug(f"can not use issubclass on {input_options}")

    try:
        return dict(**input_options)
    except TypeError as err:
        msg = f"Input options is not known: {type(input_options)}"
        raise TypeError(msg) from err


def _create_argparse_options(name: str, field: FieldInfo) -> tuple[str, dict[str, Any]]:
    """
    Convert a pydantic Field into ``dict`` to splat into ArgumentParser.add_argument.

    Args:
        name (str): Attribute name.
        field (FieldInfo): Attribute information.

    Raises:
        ValueError: If `nargs` can't be determined.

    Returns:
        tuple[str, dict[str, Any]]: Argparse options

    """
    field_name = name if field.is_required() else "--" + name.replace("_", "-")

    field_type = get_origin(field.annotation)
    field_args = get_args(field.annotation)
    iterable_types = (list, tuple, set)

    options = {"action": "store", "help": field.description, "default": field.default}

    if field.annotation is bool:
        options["action"] = "store_false" if field.default else "store_true"

    # if field_type is in (list, tuple, set) OR if (list, tuple, set) | Any
    elif field_type in iterable_types or (
        field_type is UnionType and any(get_origin(p) in iterable_types for p in field_args)
    ):
        nargs: str | int = "+"

        # If the field is a tuple, and the Ellipsis is not present
        # We can assume that the nargs is the length of the tuple
        if field_type is tuple and Ellipsis not in field_args:
            nargs = len(field_args)

        # Now we handle unions, but do the same check as above
        elif field_type is UnionType and Ellipsis not in field_args:
            for arg in field_args:
                args = get_args(arg)
                if arg is not NoneType and type(args) is tuple and Ellipsis not in args:
                    nargs = len(args)

        if nargs == 0:
            msg = f"Unable to determine nargs for {name=}, got {nargs=}"
            raise ValueError(msg)
        options["nargs"] = nargs

    return field_name, options


def add_options_to_parser(
    parser: ArgumentParser,
    options_class: type[BaseOptions],
    description: str | None = None,
) -> ArgumentParser:
    """
    Add options to a parser.

    Given an established argument parser and a class derived
    from a ``pydantic.BaseModel``, populate the argument parser
    with the model properties.

    Args:
        parser (ArgumentParser): Parser that arguments will be added to
        options_class (type[BaseModel]): A ``Options`` style class derived from
        ``BaseOptions``
        description (str | None, optional): parser description. Defaults to None.

    Returns:
        ArgumentParser: Updated argument parser

    """
    assert issubclass(options_class, BaseModel), (  # noqa: S101
        f"{options_class=} is not a pydantic BaseModel"
    )

    group = parser.add_argument_group(
        title=f"Inputs for {options_class.__name__}",
        description=description,
    )

    for name, field in options_class.model_fields.items():
        field_name, options = _create_argparse_options(name=name, field=field)
        try:
            group.add_argument(field_name, **options)
        except Exception as e:
            msg = f"{field_name=} {options=}"
            raise ValueError(msg) from e

    return parser


U = TypeVar("U", bound=BaseOptions)


def create_options_from_parser(
    parser_namespace: Namespace,
    options_class: type[U],
) -> U:
    """
    Create options class from an argparse parser.

    Given a ``BaseOptions`` derived class, extract the corresponding
    arguments from an ``argparse.nNamespace``. These options correspond to
    ones generated by ``add_options_to_parser``.

    Args:
        parser_namespace (Namespace): The argument parser corresponding to those in the
        ``BaseOptions`` class
        options_class (U): A ``BaseOptions`` derived class

    Returns:
        U: An populated options class with arguments drawn from CLI argument parser

    """
    assert issubclass(  # noqa: S101
        options_class,
        BaseModel,
    ), f"{options_class=} is not a pydantic BaseModel"

    args = vars(parser_namespace) if not isinstance(parser_namespace, dict) else parser_namespace

    opts_dict = {}
    for name in options_class.model_fields:
        opts_dict[name] = args[name]

    return options_class(**opts_dict)
