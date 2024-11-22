from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Generator, Iterator

if TYPE_CHECKING:
    from makem4b.models import ProbedFile


def enumerate_timestamped_files(files: list[ProbedFile]) -> Iterator[tuple[str, int, int]]:
    start_ts = 1
    for idx, file in enumerate(files):
        end_ts = start_ts + file.stream.duration_ts
        yield idx, start_ts, end_ts, file
        start_ts = end_ts + 1


@contextmanager
def generate_metadata(files: list[ProbedFile]) -> Generator[Path, None, None]:
    print("\nGenerating metadata and chapters ...")
    with NamedTemporaryFile("w", prefix="makem4b_metadata_out_") as tempfile:
        for idx, start_ts, end_ts, file in enumerate_timestamped_files(files):
            if idx == 0:
                tempfile.write(file.metadata.to_tags())
            tempfile.write(file.metadata.to_chapter(start_ts, end_ts))
        tempfile.flush()
        yield Path(tempfile.name)
