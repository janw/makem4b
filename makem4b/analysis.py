from __future__ import annotations

from typing import TYPE_CHECKING

from rich import box, get_console
from rich.progress import track
from rich.table import Table

from makem4b import constants, ffmpeg
from makem4b.emoji import Emoji
from makem4b.models import Metadata, ProbedFile, ProbeResult, ProcessingMode, Stream
from makem4b.utils import pinfo

if TYPE_CHECKING:
    from pathlib import Path


def _probe_file(file: Path) -> ProbedFile:
    media = ffmpeg.probe(file)
    has_cover = False
    audio = None
    for idx, stream in enumerate(media.get("streams", [])):
        if (ctype := stream.get("codec_type", "")) == "audio":
            audio = (idx, stream)
        elif ctype == "video" and bool(stream.get("disposition", {}).get("attached_pic", 0)):
            has_cover = True

    if not audio:
        msg = f"File {file} contains no usable audio stream"
        raise ValueError(msg)

    return ProbedFile(
        filename=file,
        stream_idx=audio[0],
        stream=Stream.model_validate(audio[1]),
        metadata=Metadata.model_validate_strings(
            media.get("format", {}).get("tags", {}),
        ),
        has_cover=has_cover,
    )


def probe_files(files_to_probe: list[Path]) -> ProbeResult:
    pinfo(Emoji.ANALYZE, f"Analyzing {len(files_to_probe)} files")
    return ProbeResult(
        files=[
            _probe_file(file)
            for file in track(
                sorted(files_to_probe),
                description="Analyzing",
                transient=True,
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
        footer=f"{codec.bit_rate:.1f} kBit/s",
    )
    table.add_column(
        "Sample Rate",
        justify="right",
        no_wrap=True,
        footer=f"{codec.sample_rate:.1f} kHz",
    )
    table.add_column(
        "Channels",
        justify="right",
        no_wrap=True,
        footer=f"{codec.channels:d}",
    )
    table.add_column(
        "Files",
        "Can be remuxed " + Emoji.REMUX if mode == ProcessingMode.REMUX else "Requires transcoding " + Emoji.TRANSCODE,
    )

    for codec, files in probed.seen_codecs.items():
        table.add_row(
            codec.codec_name,
            f"{codec.bit_rate:.1f} kBit/s",
            f"{codec.sample_rate:.1f} kHz",
            f"{codec.channels:d}",
            "\n".join(str(f.relative_to(constants.CWD)) for f in files),
        )

    get_console().print(table)
