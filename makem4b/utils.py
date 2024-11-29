from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING, Any, NamedTuple

from rich import get_console

from makem4b.emoji import Emoji

if TYPE_CHECKING:
    from pathlib import Path

    from rich.progress import Progress, TaskID


def pinfo(emoji: Emoji = Emoji.INFO, *objects: Any, **print_kwargs: Any) -> None:
    get_console().print(emoji, *objects, **print_kwargs)


class TaskProgress(NamedTuple):
    progress: Progress
    task_id: TaskID

    @classmethod
    def make(cls, progress: Progress, **task_kwargs: Any) -> TaskProgress:
        return cls(progress=progress, task_id=progress.add_task(**task_kwargs))

    def update(self, **update_kwargs: Any) -> None:
        self.progress.update(self.task_id, **update_kwargs)

    def close(self) -> None:
        self.progress.remove_task(self.task_id)


def escape_concat_filename(val: Path) -> str:
    re_escape = re.compile(r"([^a-zA-Z0-9\/\._-])")
    return re_escape.sub(r"\\\1", str(val.absolute()))


def copy_mtime(from_: Path, to: Path) -> None:
    stat = from_.stat()
    os.utime(to, (stat.st_atime, stat.st_mtime))
