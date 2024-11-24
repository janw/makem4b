from __future__ import annotations

from typing import TYPE_CHECKING

from rich import print as rprint
from tqdm import tqdm

from makem4b import ffmpeg
from makem4b.models import Metadata, ProbedFile, ProbeResult, Stream

if TYPE_CHECKING:
    from collections.abc import Iterable
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


def probe_files(files_to_probe: Iterable[Path]) -> ProbeResult:
    rprint("[b]Analyzing files ...[/]")
    return ProbeResult(
        files=[_probe_file(file) for file in tqdm(sorted(files_to_probe), leave=False)],
    )
