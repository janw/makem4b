import re
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Generator, Iterator

from makem4b import ffmpeg
from makem4b.models import ProbedFile

METADATA_TIMEBASE = 1000
METADATA_CHAPTER_TMPL = """

[CHAPTER]
TIMEBASE=1/1000
START={start_ts}
END={end_ts}
title={title}
"""

re_title = re.compile(r"^title=(.+)$", re.MULTILINE)
re_chapter = re.compile(r"^\[CHAPTER\]$", re.MULTILINE)


def truncate_primary_metadata(metadata: str) -> str:
    if match := re_chapter.search(metadata):
        return metadata[: match.start()]
    return metadata


def iterate_probed_file_metadata(files: list[ProbedFile]) -> Iterator[tuple[str, int, int]]:
    start_ts = 1
    for file in files:
        metadata = ffmpeg.get_metadata(file.filename)
        end_ts = start_ts + file.duration
        yield metadata, start_ts, end_ts
        start_ts = end_ts + 1


@contextmanager
def generate_metadata(files: list[ProbedFile]) -> Generator[Path, None, None]:
    print("\nGenerating metadata and chapters ...")
    with NamedTemporaryFile("w", prefix="makem4b_metadata_out_") as tempfile:
        for idx, (metadata, start_ts, end_ts) in enumerate(iterate_probed_file_metadata(files)):
            if idx == 0:
                tempfile.write(truncate_primary_metadata(metadata))
            title = match.group(1) if (match := re_title.search(metadata)) else f"Part {idx+1}"
            tempfile.write(
                METADATA_CHAPTER_TMPL.format(
                    start_ts=start_ts,
                    end_ts=end_ts,
                    title=title,
                )
            )
        tempfile.flush()
        yield Path(tempfile.name)
