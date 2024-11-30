from __future__ import annotations

import re
from bisect import bisect_left
from collections import defaultdict
from contextlib import suppress
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Literal, NamedTuple

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidatorFunctionWrapHandler,
    WrapValidator,
    model_validator,
)

from makem4b import constants
from makem4b.emoji import Emoji
from makem4b.utils import pinfo

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

re_escape = re.compile(r"([=;#\\\n])")
re_filename = re.compile(r"[/\\?%*:|\"<>\x7F\x00-\x1F]")


def escape_ffmetadata(val: str) -> str:
    return re_escape.sub(r"\\\1", val)


def escape_filename(val: str) -> str:
    return re_filename.sub("-", val)


def validate_stream(val: dict, handler: ValidatorFunctionWrapHandler) -> AudioStream | BaseStream | None:
    with suppress(ValidationError):
        return handler(val)
    return None


class ProcessingMode(StrEnum):
    REMUX = "Remux"
    TRANSCODE_UNIFORM = "Transcode Uniform"
    TRANSCODE_MIXED = "Transcode Mixed"


class CodecParams(NamedTuple):
    codec_name: str
    sample_rate: float
    bit_rate: float
    channels: int


class _StreamDisposition(BaseModel):
    attached_pic: int = 0


class BaseStream(BaseModel):
    model_config = ConfigDict(extra="ignore")

    disposition: _StreamDisposition = _StreamDisposition()
    codec_type: str


class AudioStream(BaseStream):
    model_config = ConfigDict(extra="ignore")

    codec_type: Literal["audio"]
    codec_name: str
    sample_rate: float
    bit_rate: float
    channels: int
    duration: float

    side_data_list: list[dict] = []

    @property
    def duration_ts(self) -> int:
        return round(self.duration * constants.TIMEBASE)

    def __eq__(self, o: object) -> bool:
        if isinstance(o, AudioStream):
            return self.codec_name == o.codec_name and self.sample_rate == o.sample_rate and self.channels == o.channels
        return super().__eq__(o)


class Metadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    album: str = ""
    artist: str = ""
    album_artist: str = ""
    composer: str = ""
    date: str = ""
    disc: str = ""
    genre: str = ""
    title: str = ""
    track: str = ""
    series: str = Field("", alias="SERIES")
    series_part: str = Field("", alias="SERIES-PART")
    movementname: str = Field("", alias="MOVEMENTNAME")
    movement: str = Field("", alias="MOVEMENT")
    narrated_by: str = Field("", alias="NARRATEDBY")
    subtitle: str = Field(
        "",
        validation_alias=AliasChoices("TIT3", "SUBTITLE"),
        serialization_alias="TIT3",
    )
    encoder: str = Field("", exclude=True)
    comment: str = ""
    grouping: str = ""

    @model_validator(mode="after")
    def sync_fields(self) -> Metadata:
        if self.series and not self.movementname:
            self.movementname = self.series
        elif self.movementname and not self.series:
            self.series = self.movementname

        if self.series_part and not self.movement:
            self.movement = self.series_part
        elif self.movement and not self.series_part:
            self.series_part = self.movement

        if not self.grouping and self.series and self.series_part:
            self.grouping = f"{self.series} #{self.series_part}"

        if self.artist and not self.album_artist:
            self.album_artist = self.artist

        return self

    def to_tags(self) -> str:
        copied = self.model_copy()
        copied.title = copied.album or copied.title
        copied.track = "1"
        copied.disc = "1"

        tags = [
            f"{field}={escape_ffmetadata(value)}"
            for field, value in copied.model_dump(
                mode="json",
                exclude_unset=True,
                exclude_none=True,
                exclude_defaults=True,
                by_alias=True,
            ).items()
        ]
        return "\n".join(tags) + "\n"

    def to_chapter(self, start_ts: int, end_ts: int) -> str:
        props = [
            constants.CHAPTER_HEADER,
            f"START={start_ts}",
            f"END={end_ts}",
            f"title={self.title}",
        ]
        return "\n" + "\n".join(props) + "\n"


StreamOrNone = Annotated[AudioStream | BaseStream | None, WrapValidator(validate_stream)]


class FFProbeFormat(BaseModel):
    tags: Metadata


class FFProbeOutput(BaseModel):
    streams: list[StreamOrNone] = []
    format_: FFProbeFormat = Field(alias="format")


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
        if len(seen_codecs := self.seen_codecs) == 1:
            codec = list(seen_codecs.keys())[0]
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
    def total_duration(self) -> int:
        return round(sum(f.stream.duration for f in self))

    def __iter__(self) -> Iterator[ProbedFile]:
        yield from self.files

    def __len__(self) -> int:
        return len(self.files)
