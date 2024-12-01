from __future__ import annotations

from typing import TYPE_CHECKING

from click.exceptions import Exit
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


def probe_files(
    files: list[Path],
    *,
    analyze_only: bool,
    no_transcode: bool,
    prefer_remux: bool,
    disable_progress: bool = False,
) -> ProbeResult:
    pinfo(Emoji.ANALYZE, f"Analyzing {len(files)} files")

    result = ProbeResult(files=[])
    for file in track(
        sorted(files),
        description="Analyzing",
        transient=True,
        disable=disable_progress,
    ):
        probed_file = _probe_file(file)
        result.add(probed_file)

        if exit_code := result.check_should_bail(
            analyze_only=analyze_only,
            no_transcode=no_transcode,
            prefer_remux=prefer_remux,
        ):
            raise Exit(exit_code)

    return result


def print_probe_result(probed: ProbeResult) -> None:
    table = Table(box=box.SIMPLE, show_footer=True)
    if not probed.processing_params:
        pinfo(Emoji.NO_FILES, "No results to show.")
        return

    mode, codec = probed.processing_params
    table.add_column(
        "Codec",
        no_wrap=True,
    )
    table.add_column(
        "Bit Rate",
        justify="right",
        no_wrap=True,
        footer=f"{codec.bit_rate/1000:.3f} kBit/s",
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
            f"{codec.bit_rate/1000:.3f} kBit/s",
            f"{codec.sample_rate/1000:.1f} kHz",
            f"{codec.channels:d}",
            "\n".join(str(f.relative_to(constants.CWD)) for f in files),
        )

    get_console().print(table)
