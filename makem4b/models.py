from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, NamedTuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from makem4b import constants

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def escape_ffmetadata(val: str) -> str:
    re_escape = re.compile(r"([=;#\\])")
    return re_escape.sub(r"\\\1", val)


class ProcessingMode(StrEnum):
    REMUX = "Remux"
    TRANSCODE_UNIFORM = "Transcode Uniform"
    TRANSCODE_MIXED = "Transcode Mixed"


class CodecParams(NamedTuple):
    codec_name: str
    sample_rate: float
    bit_rate: float
    channels: int


class Stream(BaseModel):
    model_config = ConfigDict(extra="ignore")

    codec_name: str
    sample_rate: float
    bit_rate: float
    channels: int
    duration: float

    @property
    def duration_ts(self) -> int:
        return int(self.duration * constants.TIMEBASE)

    def __eq__(self, o: object) -> bool:
        if isinstance(o, Stream):
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
    subtitle: str = Field("", validation_alias="SUBTITLE", serialization_alias="TIT3")
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


@dataclass
class ProbedFile:
    filename: Path
    stream_idx: int

    stream: Stream
    metadata: Metadata

    has_cover: bool = False

    @property
    def codec_params(self) -> CodecParams:
        return CodecParams(
            codec_name=self.stream.codec_name,
            sample_rate=round(self.stream.sample_rate / 1000, 1),
            bit_rate=round(self.stream.bit_rate / 1000, 1),
            channels=self.stream.channels,
        )

    def to_filename_stem(self) -> str:
        metadata = self.metadata
        if not metadata.artist and not metadata.album:
            return self.filename.stem + "_merged"

        stem = f"{metadata.artist} -"
        if (grp := metadata.grouping) and grp not in metadata.album:
            stem += f" {grp} -"
        stem += f" {metadata.album}"
        return stem


@dataclass
class ProbeResult:
    files: list[ProbedFile]

    processing_params: tuple[ProcessingMode, CodecParams] = field(init=False)
    seen_codecs: dict[CodecParams, list[Path]] = field(init=False)

    def __post_init__(self) -> None:
        self.seen_codecs = self._generate_seen_codecs()
        self.processing_params = self._generate_processing_params()

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
    def total_duration(self) -> int:
        return round(sum(f.stream.duration for f in self))

    def __iter__(self) -> Iterator[ProbedFile]:
        yield from self.files

    def __len__(self) -> int:
        return len(self.files)
