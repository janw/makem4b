from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, NamedTuple

from makem4b import constants
from makem4b.emoji import Emoji
from makem4b.models import AudioStream, FFProbeOutput, Metadata
from makem4b.utils import escape_filename, pinfo

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

from collections.abc import Callable
from typing import Any, TypeVar

from rich_click import Command, RichCommand

_AnyCallable = Callable[..., Any]

Cmd = TypeVar("Cmd", bound=_AnyCallable | Command | RichCommand)
CmdOption = Callable[[Cmd], Cmd]


class ProcessingMode(StrEnum):
    REMUX = "Remux"
    REMUX_FIX_DTS = "Remux and fix DTS"  # TODO: implement
    TRANSCODE_UNIFORM = "Transcode Uniform"
    TRANSCODE_MIXED = "Transcode Mixed"


class CodecParams(NamedTuple):
    codec_name: str
    sample_rate: float
    bit_rate: float
    channels: int


@dataclass
class ProbedFile:
    filename: Path
    stream: AudioStream
    metadata: Metadata
    has_cover: bool
    output_filename_stem: str = field(init=False)

    @classmethod
    def from_ffmpeg_probe_output(cls, data: FFProbeOutput, *, file: Path) -> ProbedFile:
        has_cover = False
        audio = None
        for stream in data.streams:
            if not stream:
                continue
            if isinstance(stream, AudioStream):
                audio = stream
            elif stream.codec_type == "video" and bool(stream.disposition.attached_pic):
                has_cover = True

        if not audio:
            msg = f"File {file} contains no usable audio stream"
            raise ValueError(msg)

        return cls(
            filename=file,
            stream=audio,
            metadata=data.format_.tags,
            has_cover=has_cover,
        )

    def __post_init__(self) -> None:
        self.output_filename_stem = self._make_stem()

    @property
    def codec_params(self) -> CodecParams:
        return CodecParams(
            codec_name=self.stream.codec_name,
            sample_rate=round(self.stream.sample_rate, 1),
            bit_rate=round(self.stream.bit_rate, 1),
            channels=self.stream.channels,
        )

    def _make_stem(self) -> str:
        metadata = self.metadata
        if not metadata.artist and not metadata.album:
            return self.filename.stem + "_merged"

        stem = f"{metadata.artist} -"
        if (grp := metadata.grouping) and grp not in metadata.album:
            stem += f" {grp} -"
        stem += f" {metadata.album}"
        return escape_filename(stem)

    @property
    def matches_prospective_output(self) -> bool:
        return self.filename.stem == self.output_filename_stem


@dataclass
class ProbeResult:
    files: list[ProbedFile]

    processing_params: tuple[ProcessingMode, CodecParams] = field(init=False)
    seen_codecs: dict[CodecParams, list[Path]] = field(init=False)

    def __post_init__(self) -> None:
        self._remove_prospective_output()
        self.seen_codecs = self._generate_seen_codecs()
        self.processing_params = self._generate_processing_params()

    def _remove_prospective_output(self) -> None:
        clean_files = []
        for file in self.files:
            if file.matches_prospective_output:
                pinfo(
                    Emoji.EVADED_DRAGONS,
                    "Removed input that looks too much like the prospective output:",
                    file.filename.name,
                    style="yellow",
                )
                continue

            clean_files.append(file)
        self.files = clean_files

    def _generate_seen_codecs(self) -> dict[CodecParams, list[Path]]:
        codecs: dict[CodecParams, list[Path]] = defaultdict(list)
        for file in self.files:
            codecs[file.codec_params].append(file.filename)
        return codecs

    def _generate_processing_params(self) -> tuple[ProcessingMode, CodecParams]:
        seen_codecs = list(self.seen_codecs.keys())
        if len(seen_codecs) == 1:
            codec = seen_codecs[0]
            mode = (
                ProcessingMode.REMUX
                if codec.codec_name in constants.SUPPORT_REMUX_CODECS
                else ProcessingMode.TRANSCODE_UNIFORM
            )
            return mode, codec

        max_bit_rate = 0.0
        max_sample_rate = 0.0
        min_channels = 9999
        for codec in seen_codecs:
            if (fbr := codec.bit_rate) > max_bit_rate:
                max_bit_rate = fbr
            if (fsr := codec.sample_rate) > max_sample_rate:
                max_sample_rate = fsr
            if (fch := codec.channels) < min_channels:
                min_channels = fch

        idx = bisect_left(constants.AAC_SAMPLE_RATES, max_sample_rate)
        target_sample_rate = constants.AAC_SAMPLE_RATES[idx]
        return ProcessingMode.TRANSCODE_MIXED, CodecParams(
            "aac",
            sample_rate=target_sample_rate,
            bit_rate=max_bit_rate,
            channels=min_channels,
        )

    @property
    def first(self) -> ProbedFile:
        return self.files[0]

    @property
    def approx_size(self) -> int:
        return sum(f.stream.approx_size for f in self)

    def __iter__(self) -> Iterator[ProbedFile]:
        yield from self.files

    def __len__(self) -> int:
        return len(self.files)
