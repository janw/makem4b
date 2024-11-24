from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def escape_ffmetadata(val: str) -> str:
    re_escape = re.compile(r"([=;#\\])")
    return re_escape.sub(r"\\\1", val)


class Stream(BaseModel):
    model_config = ConfigDict(extra="ignore")

    codec_name: str
    bit_rate: float
    sample_rate: float
    channels: int
    duration: float

    @property
    def duration_ts(self) -> int:
        return int(self.duration * 10e9)

    def __eq__(self, o: object) -> bool:
        if isinstance(o, Stream):
            return (
                self.codec_name == o.codec_name
                and self.bit_rate == o.bit_rate
                and self.sample_rate == o.sample_rate
                and self.channels == o.channels
            )
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
    def sync_series_and_movement(self) -> Metadata:
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
            "[CHAPTER]",
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


@dataclass(slots=True)
class ProbeResult:
    files: list[ProbedFile]

    @property
    def allows_copying(self) -> bool:
        for file in self.files:
            if file.stream != self.first.stream:
                return False
        return self.first.stream.codec_name in ("aac", "libfdk_aac")

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
