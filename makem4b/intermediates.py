from __future__ import annotations

from typing import TYPE_CHECKING

from rich.progress import Progress

from makem4b import ffmpeg
from makem4b.emoji import Emoji
from makem4b.types import ProcessingMode
from makem4b.utils import TaskProgress, escape_concat_filename, pinfo

if TYPE_CHECKING:
    from pathlib import Path

    from makem4b.types import ProbeResult


def generate_intermediates(
    probed: ProbeResult, *, tmpdir: Path, prefer_remux: bool, disable_progress: bool = False
) -> tuple[list[Path], list[int]]:
    mode, codec = probed.processing_params
    specs_msg = f"({codec.bit_rate/1000:.1f} kBit/s, {codec.sample_rate/1000:.1f} kHz)"

    if mode == ProcessingMode.REMUX:
        pinfo(Emoji.REMUX, "Using input files as-is", specs_msg)
        return [f.filename for f in probed.files], [f.stream.duration_ts for f in probed.files]

    if mode == ProcessingMode.REMUX_FIX_DTS or (mode == ProcessingMode.TRANSCODE_UNIFORM and prefer_remux):
        pinfo(Emoji.AVOIDING_TRANSCODE, "Remuxing", specs_msg)
        args = ffmpeg.COPY_CMD_ARGS
    else:
        pinfo(Emoji.TRANSCODE, "Transcoding files", specs_msg)
        args = ffmpeg.make_transcoding_args(codec)

    intermediates: list[Path] = []
    durations: list[int] = []
    with Progress(transient=True, disable=disable_progress) as progress:
        for idx, file in enumerate(progress.track(probed, description="Processing files"), 1):
            outfilen = tmpdir / f"intermediate_{idx:05d}.ts"
            ffmpeg.convert(
                [file.filename],
                args,
                output=outfilen,
                progress=TaskProgress.make(
                    progress,
                    # FFmpeg does not report out_time when writing mpeg2ts, so we're
                    # falling back to a very crude approximation of progress via total_size.
                    total=1.1 * file.stream.approx_size,
                    description=file.filename.name,
                ),
            )
            duration_ts = ffmpeg.probe_duration(outfilen)
            intermediates.append(outfilen)
            durations.append(duration_ts)
    return intermediates, durations


def generate_concat_file(intermediates: list[Path], *, tmpdir: Path) -> Path:
    concat_file = tmpdir / "concat.txt"
    concat_file.write_text("\n".join(f"file {escape_concat_filename(i)}" for i in intermediates) + "\n")
    return concat_file
