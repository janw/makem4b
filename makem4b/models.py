from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Codec:
    name: str
    bit_rate: float
    sample_rate: float
    channels: int


@dataclass(slots=True)
class ProbedFile:
    filename: Path
    stream_idx: int
    duration: int
    codec: Codec


@dataclass(slots=True)
class ProbeResult:
    files: list[ProbedFile]

    @property
    def can_copy(self) -> bool:
        first = None
        for f in self.files:
            if not first:
                first = f.codec
            elif f.codec != first:
                return False
        return first.name in ("aac", "libfdk_aac")
