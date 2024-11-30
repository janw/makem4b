from __future__ import annotations

from contextlib import suppress
from typing import Annotated, Any, Literal

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
from makem4b.utils import escape_ffmetadata, parse_grouping


def validate_stream(val: dict[str, Any], handler: ValidatorFunctionWrapHandler) -> AudioStream | BaseStream | None:
    with suppress(ValidationError):
        return handler(val)
    return None


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

    side_data_list: list[dict[str, Any]] = []

    @property
    def duration_ts(self) -> int:
        return round(self.duration * constants.TIMEBASE)

    @property
    def approx_size(self) -> int:
        bps = self.bit_rate / 8
        return round(self.duration * bps)

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
    grouping: str = Field(
        "",
        validation_alias=AliasChoices("grouping", "GRP1", "TIT1"),
        serialization_alias="grouping",
    )

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

        if self.series and self.series_part:
            self.grouping = f"{self.series} #{self.series_part}"
        elif self.grouping and (grp_match := parse_grouping(self.grouping)):
            self.series, self.series_part = grp_match
            self.movementname, self.movement = grp_match

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
    tags: Metadata = Metadata()


class FFProbeOutput(BaseModel):
    streams: list[StreamOrNone] = []
    format_: FFProbeFormat = Field(alias="format")
