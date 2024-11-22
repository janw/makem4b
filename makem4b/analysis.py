from pathlib import Path
from typing import Iterable

from makem4b import ffmpeg
from makem4b.models import Metadata, ProbedFile, ProbeResult, Stream


def _probe_file(file: Path) -> ProbedFile:
    media = ffmpeg.probe(file)
    for idx, stream in enumerate(media.get("streams", [])):
        if stream.get("codec_type", "") != "audio":
            continue
        result = ProbedFile(
            filename=file,
            stream_idx=idx,
            stream=Stream.model_validate(stream),
            metadata=Metadata.model_validate_strings(media.get("format", {}).get("tags", {})),
        )

        print(f" -> {file}: {result.stream}")
        return result
    raise ValueError(f"File {file} contains no usable audio stream")


def probe_files(files_to_probe: Iterable[Path]) -> ProbeResult:
    print("Analyzing files ...")
    return ProbeResult(files=[_probe_file(file) for file in sorted(files_to_probe)])
