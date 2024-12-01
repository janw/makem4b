from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from statistics import variance
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


class ExitCode(IntEnum):
    SUCCESS = 0
    GENERIC_ERROR = 1
    USAGE_ERROR = 2
    TARGET_EXISTS = 4
    NO_TRANSCODE = 8


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

    @staticmethod
    def _codecs_match_loosely(seen_codecs: list[CodecParams]) -> bool:
        cn = seen_codecs[0].codec_name
        sr = seen_codecs[0].sample_rate
        ch = seen_codecs[0].channels

        bit_rates = [seen_codecs[0].bit_rate]
        for params in seen_codecs[1:]:
            if params.codec_name != cn or params.sample_rate != sr or params.channels != ch:
                return False
            bit_rates.append(params.bit_rate)

        # This might be a terrible assumption to make but in my testing this
        # did not cause any issues in playback or chapter alignment: If the variance
        # between bit rates is less than 128 bits, remuxing files works just fine.
        return variance(bit_rates) < 128

    def _generate_processing_params(self) -> tuple[ProcessingMode, CodecParams]:
        seen_codecs = list(self.seen_codecs.keys())
        first_seen = seen_codecs[0]
        mode = (
            ProcessingMode.REMUX
            if first_seen.codec_name in constants.SUPPORT_REMUX_CODECS
            else ProcessingMode.TRANSCODE_UNIFORM
        )
        if len(seen_codecs) == 1 or self._codecs_match_loosely(seen_codecs):
            return mode, first_seen

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

        return ProcessingMode.TRANSCODE_MIXED, CodecParams(
            "aac",
            sample_rate=max_sample_rate,
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
