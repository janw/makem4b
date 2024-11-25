from __future__ import annotations

from typing import TYPE_CHECKING

from rich.progress import Progress

from makem4b import ffmpeg
from makem4b.emoji import Emoji
from makem4b.models import ProcessingMode
from makem4b.utils import TaskProgress, escape_concat_filename, pinfo

if TYPE_CHECKING:
    from pathlib import Path

    from makem4b.models import ProbeResult


def generate_intermediates(probed: ProbeResult, *, tmpdir: Path, avoid_transcode: bool) -> list[Path]:
    mode, codec = probed.processing_params
    specs_msg = f"({codec.bit_rate:.1f} kBit/s, {codec.sample_rate:.1f} kHz)"
    if mode == ProcessingMode.REMUX or mode == ProcessingMode.TRANSCODE_UNIFORM and avoid_transcode:
        pinfo(Emoji.REMUX, "Using input files as-is", specs_msg)
        return [p.filename for p in probed]

    pinfo(Emoji.TRANSCODE, "Transcoding files", specs_msg)
    args = ffmpeg.make_transcoding_args(codec)
    intermediates: list[Path] = []
    with Progress(transient=True) as progress:
        for file in progress.track(probed, description="Transcoding files"):
            outfilen = tmpdir / (file.filename.stem + ".intermed.aac")
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
    return intermediates


def generate_concat_file(intermediates: list[Path], *, tmpdir: Path) -> Path:
    concat_file = tmpdir / "concat.txt"
    concat_file.write_text("\n".join(f"file {escape_concat_filename(i)}" for i in intermediates) + "\n")
    return concat_file
