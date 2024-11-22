from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

DURATION_TIMEBASE = 1000


class Stream(BaseModel):
    model_config = ConfigDict(extra="ignore")

    codec_name: str
    bit_rate: float
    sample_rate: float
    channels: int
    duration: float

    @property
    def duration_ts(self) -> int:
        return round(self.duration * DURATION_TIMEBASE)


class Metadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = ""
    artist: str = ""
    album: str = ""
    album_artist: str = ""
    composer: str = ""
    date: str = ""
    genre: str = ""
    track: str = ""
    disc: str = ""
    audible_asin: str = Field("", alias="AUDIBLE_ASIN")
    language: str = Field("", alias="LANGUAGE")
    part: str = Field("", alias="PART")
    series: str = Field("", alias="SERIES")
    series_part: str = Field("", alias="SERIES-PART")
    subtitle: str = Field("", alias="SUBTITLE")
    comment: str = ""

    def to_tags(self) -> str:
        copied = self.model_copy()
        copied.title = copied.album or copied.title
        copied.track = "1"
        copied.disc = "1"

        tags = [
            f"{field}={value}"
            for field, value in copied.model_dump(
                mode="json",
                exclude_unset=True,
                exclude_none=True,
                exclude_defaults=True,
            ).items()
        ]
        return ";FFMETADATA1\n" + "\n".join(tags) + "\n"

    def to_chapter(self, start_ts: int, end_ts: int) -> str:
        props = [
            "[CHAPTER]",
            f"TIMEBASE=1/{DURATION_TIMEBASE}",
            f"START={start_ts}",
            f"END={end_ts}",
            f"title={self.title}",
        ]
        return "\n\n" + "\n".join(props) + "\n"


@dataclass
class ProbedFile:
    filename: Path
    stream_idx: int

    stream: Stream
    metadata: Metadata


@dataclass(slots=True)
class ProbeResult:
    files: list[ProbedFile]

    @property
    def can_copy(self) -> bool:
        first = None
        for file in self.files:
            if not first:
                first = file
            elif file.stream != first:
                return False
        return first.name in ("aac", "libfdk_aac")
