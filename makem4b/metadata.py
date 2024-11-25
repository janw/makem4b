from __future__ import annotations

from typing import TYPE_CHECKING

from makem4b import ffmpeg
from makem4b.emoji import Emoji
from makem4b.utils import pinfo

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from makem4b.models import ProbedFile, ProbeResult

FFMPEG_METADATA_HEADER = ";FFMETADATA1\n"


def enumerate_timestamped_files(
    probed: ProbeResult,
) -> Iterator[tuple[int, int, int, ProbedFile]]:
    start_ts = 1
    for idx, file in enumerate(probed):
        end_ts = start_ts + file.stream.duration_ts
        yield idx, start_ts, end_ts, file
        start_ts = end_ts + 1


def generate_metadata(probed: ProbeResult, *, tmpdir: Path) -> Path:
    pinfo(Emoji.METADATA, "Generating metadata and chapters")
    metadata_file = tmpdir / "metadata.txt"
    with metadata_file.open("w") as fh:
        fh.write(FFMPEG_METADATA_HEADER)
        for idx, start_ts, end_ts, file in enumerate_timestamped_files(probed):
            if idx == 0:
                fh.write(file.metadata.to_tags())
            fh.write(file.metadata.to_chapter(start_ts, end_ts))
        fh.flush()
    return metadata_file


def extract_cover_img(probed: ProbeResult, *, tmpdir: Path) -> Path | None:
    if not probed.first.has_cover:
        return None
    pinfo(Emoji.COVER, "Extracting cover image")
    cover_file = tmpdir / "cover.mp4"
    ffmpeg.extract_cover_img(probed.first.filename, output=cover_file)
    return cover_file
