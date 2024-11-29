from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Concatenate, ParamSpec, TypeVar

import rich_click as click

from makem4b.cli import options
from makem4b.cli.env import Environment

if TYPE_CHECKING:
    from collections.abc import Callable

    import makem4b.types as mt

P = ParamSpec("P")
R = TypeVar("R")

pass_env = click.make_pass_decorator(Environment, ensure=True)


def pass_ctx_and_env(f: Callable[Concatenate[click.RichContext, Environment, P], R]) -> Callable[P, R]:
    return pass_env(click.pass_context(f))


def add_options(options: list[click.Parameter]) -> Callable[[mt.Cmd], mt.Cmd]:
    def _add_options(f: mt.Cmd) -> mt.Cmd:
        for option in reversed(options):
            if isinstance(f, click.Command | click.RichCommand):
                f.params.append(option)
            else:
                if not hasattr(f, "__click_params__"):
                    f.__click_params__ = []  # type: ignore

                f.__click_params__.append(option)  # type: ignore

        return f

    return _add_options


add_processing_options = add_options(options.PROCESSING_OPTIONS)
