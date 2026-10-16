"""Type checking of ``BaseOptions.with_options`` keyword arguments."""

from __future__ import annotations

import os

import pytest
from mypy import api

SNIPPET = """
from pathlib import Path
from typing import Any, assert_type

from capn_crunch import BaseOptions


class MS(BaseOptions):
    path: Path
    column: str | None = None
    beam: int | None = None


class SubMS(MS):
    flagged: bool = False


ms = MS(path=Path("a.ms"))
assert_type(ms.with_options(path=Path("b.ms")), MS)
assert_type(ms.with_options(), MS)
ms.with_options(column="DATA", beam=None)
updates: dict[str, Any] = {"beam": 1}
ms.with_options(**updates)

sub = SubMS(path=Path("a.ms"))
assert_type(sub.with_options(flagged=True), SubMS)


def update(options: BaseOptions) -> BaseOptions:
    return options.with_options()


ms.with_options(colum="DATA")  # typo
ms.with_options(beam="one")  # wrong type
sub.with_options(flagged="yes")  # wrong subclass type
"""


def _line(marker: str) -> int:
    lines = SNIPPET.splitlines()
    return next(i for i, line in enumerate(lines, start=1) if line.endswith(f"# {marker}"))


def _run_mypy(python_version: str) -> list[str]:
    stdout, stderr, _ = api.run(
        [
            "--cache-dir",
            os.devnull,
            "--python-version",
            python_version,
            "--no-error-summary",
            "--hide-error-context",
            "-c",
            SNIPPET,
        ]
    )
    assert stderr == ""
    return [line for line in stdout.splitlines() if ": error:" in line]


def test_with_options_checked_on_313():
    """When targeting 3.13+ keyword arguments are checked against the fields"""
    errors = _run_mypy("3.13")

    assert len(errors) == 3, errors
    assert errors[0].startswith(f"<string>:{_line('typo')}:")
    assert 'Unexpected keyword argument "colum"' in errors[0]
    assert errors[1].startswith(f"<string>:{_line('wrong type')}:")
    assert 'expected "int | None"' in errors[1]
    assert errors[2].startswith(f"<string>:{_line('wrong subclass type')}:")
    assert 'expected "bool"' in errors[2]


@pytest.mark.parametrize("python_version", ["3.11", "3.12"])
def test_with_options_unchecked_before_313(python_version):
    """Before 3.13 any keyword arguments are accepted, without false errors"""
    assert _run_mypy(python_version) == []
