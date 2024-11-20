from pathlib import Path
from typing import Iterable

from makem4b import ffmpeg
from makem4b.metadata import METADATA_TIMEBASE
from makem4b.models import Codec, ProbedFile, ProbeResult


def _probe_file(file: Path) -> ProbedFile:
    media = ffmpeg.probe(file)
    for idx, stream in enumerate(media.get("streams", [])):
        if stream.get("codec_type", "") != "audio":
            continue
        result = ProbedFile(
            filename=file,
            stream_idx=idx,
            duration=round(float(stream["duration"]) * METADATA_TIMEBASE),
            codec=Codec(
                bit_rate=float(stream["bit_rate"]),
                sample_rate=round(float(stream["sample_rate"]) / 10) * 10,
                channels=stream["channels"],
                name=stream["codec_name"],
            ),
        )

        print(f" -> {file}: {result.codec}")
        return result
    raise ValueError(f"File {file} contains no usable audio stream")


def probe_files(files_to_probe: Iterable[Path]) -> ProbeResult:
    print("Analyzing files ...")
    return ProbeResult(files=[_probe_file(file) for file in sorted(files_to_probe)])
