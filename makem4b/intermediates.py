from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from rich.progress import Progress

from makem4b import ffmpeg
from makem4b.emoji import Emoji
from makem4b.models import ProcessingMode
from makem4b.utils import TaskProgress, pinfo

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from makem4b.models import ProbeResult


@contextmanager
def generate_intermediates(
    probed: ProbeResult, *, keep: bool, avoid_transcode: bool
) -> Generator[list[Path], None, None]:
    mode, codec = probed.processing_params
    specs_msg = f"({codec.bit_rate:.1f} kBit/s, {codec.sample_rate:.1f} kHz)"
    suffix = ".intermed.aac"
    args = ffmpeg.COPY_CMD_ARGS
    if mode == ProcessingMode.REMUX or mode == ProcessingMode.TRANSCODE_UNIFORM and avoid_transcode:
        pinfo(Emoji.REMUX, "Remuxing individual files", specs_msg)
        if mode == ProcessingMode.TRANSCODE_UNIFORM:
            suffix = ".intermed.ts"
    elif mode in (ProcessingMode.TRANSCODE_MIXED, ProcessingMode.TRANSCODE_UNIFORM):
        pinfo(Emoji.TRANSCODE, "Transcoding files", specs_msg)
        args = ffmpeg.make_transcoding_args(codec)

    intermediates: list[Path] = []
    try:
        with Progress(transient=True) as progress:
            for file in progress.track(probed, description="Transcoding files"):
                outfilen = file.filename.with_suffix(suffix)
                intermediates.append(outfilen)
                ffmpeg.convert(
                    [file.filename],
                    args,
                    output=outfilen,
                    progress=TaskProgress.make(
                        progress,
                        total=round(file.stream.duration),
                        description=file.filename.name,
                    ),
                )
        yield intermediates
    finally:
        if not keep:
            for intermediate in intermediates:
                intermediate.unlink(missing_ok=True)
