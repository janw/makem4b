from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

from rich import get_console

from makem4b.emoji import Emoji

if TYPE_CHECKING:
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
