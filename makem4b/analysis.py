from __future__ import annotations

from typing import TYPE_CHECKING

from rich import box, get_console
from rich.progress import track
from rich.table import Table

from makem4b import constants, ffmpeg
from makem4b.emoji import Emoji
from makem4b.models import FFProbeOutput
from makem4b.types import ProbedFile, ProbeResult, ProcessingMode
from makem4b.utils import pinfo

if TYPE_CHECKING:
    from pathlib import Path


def _probe_file(file: Path) -> ProbedFile:
    output = ffmpeg.probe(file)
    ffprobed = FFProbeOutput.model_validate(output, context={"file": file})
    return ProbedFile.from_ffmpeg_probe_output(ffprobed, file=file)


def probe_files(files_to_probe: list[Path], *, disable_progress: bool = False) -> ProbeResult:
    pinfo(Emoji.ANALYZE, f"Analyzing {len(files_to_probe)} files")
    return ProbeResult(
        files=[
            _probe_file(file)
            for file in track(
                sorted(files_to_probe),
                description="Analyzing",
                transient=True,
                disable=disable_progress,
            )
        ],
    )


def print_probe_result(probed: ProbeResult) -> None:
    table = Table(box=box.SIMPLE, show_footer=True)

    mode, codec = probed.processing_params
    table.add_column(
        "Codec",
        no_wrap=True,
    )
    table.add_column(
        "Bit Rate",
        justify="right",
        no_wrap=True,
        footer=f"{codec.bit_rate/1000:.1f} kBit/s",
    )
    table.add_column(
        "Sample Rate",
        justify="right",
        no_wrap=True,
        footer=f"{codec.sample_rate/1000:.1f} kHz",
    )
    table.add_column(
        "Channels",
        justify="right",
        no_wrap=True,
        footer=f"{codec.channels:d}",
    )

    match mode:
        case ProcessingMode.TRANSCODE_MIXED:
            msg = "Requires transcoding " + Emoji.TRANSCODE
        case ProcessingMode.TRANSCODE_UNIFORM:
            msg = f"Remuxable as {probed.first.filename.suffix} (use --avoid-transcode) " + Emoji.AVOIDING_TRANSCODE
        case ProcessingMode.REMUX:
            msg = "Remuxable " + Emoji.REMUX
    table.add_column("Files", msg)

    for codec, files in probed.seen_codecs.items():
        table.add_row(
            codec.codec_name,
            f"{codec.bit_rate/1000:.1f} kBit/s",
            f"{codec.sample_rate/1000:.1f} kHz",
            f"{codec.channels:d}",
            "\n".join(str(f.relative_to(constants.CWD)) for f in files),
        )

    get_console().print(table)
