from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from rich_click import Command, RichCommand

_AnyCallable = Callable[..., Any]

Cmd = TypeVar("Cmd", bound=_AnyCallable | Command | RichCommand)
CmdOption = Callable[[Cmd], Cmd]
