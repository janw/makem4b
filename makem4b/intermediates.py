from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from rich import print as rprint
from tqdm import tqdm

from makem4b import ffmpeg

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from makem4b.models import ProbeResult


@contextmanager
def generate_intermediates(probed: ProbeResult, *, keep: bool, force_copy: bool) -> Generator[list[Path], None, None]:
    if probed.allows_copying or force_copy:
        rprint("\n[b]Remuxing individual files ...[/]")
        args = ffmpeg.COPY_CMD_ARGS
    else:
        rprint("\n[b]Transcoding individual files ...[/]")
        args = ffmpeg.make_transcoding_args(probed.first)

    intermediates: list[Path] = []
    try:
        for file in tqdm(probed, desc="Transcoding files", leave=False):
            outfilen = file.filename.with_suffix(".intermed.aac")
            intermediates.append(outfilen)
            ffmpeg.convert(
                [file.filename],
                args,
                output=outfilen,
                total=round(file.stream.duration),
                desc=file.filename.name,
            )
        yield intermediates
    finally:
        if not keep:
            for intermediate in intermediates:
                intermediate.unlink(missing_ok=True)
