from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Environment:
    verbose: bool = False
    cwd: Path = field(default_factory=Path.cwd)

    debug: bool = False
    keep_intermediates: bool = False
