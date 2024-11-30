from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from makem4b import constants

if TYPE_CHECKING:
    from collections.abc import Generator


@dataclass
class Environment:
    verbose: bool = False
    cwd: Path = field(default_factory=Path.cwd)

    debug: bool = False
    keep_intermediates: bool = False

    @contextmanager
    def handle_temp_storage(self, *, parent: Path) -> Generator[Path, None, None]:
        tmpdir = parent / "makem4b_tmpdir"
        tmpdir.mkdir(exist_ok=True)
        (tmpdir / constants.CACHEDIR_TAG).touch()
        try:
            yield tmpdir
        finally:
            if not self.keep_intermediates:
                for file in tmpdir.iterdir():
                    file.unlink(missing_ok=True)
                tmpdir.rmdir()
