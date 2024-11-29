from __future__ import annotations

import shutil
from contextlib import contextmanager
from os.path import commonpath
from pathlib import Path
from typing import TYPE_CHECKING

from click.exceptions import Exit
from rich.progress import Progress, track

from makem4b import constants, ffmpeg
from makem4b.emoji import Emoji
from makem4b.models import ProbeResult, ProcessingMode
from makem4b.utils import TaskProgress, pinfo

if TYPE_CHECKING:
    from collections.abc import Generator

CACHEDIR_TAG = "CACHEDIR.TAG"


@contextmanager
def handle_temp_storage(result: ProbeResult, *, keep: bool) -> Generator[Path, None, None]:
    tmpdir = result.first.filename.parent / "makem4b.tmp"
    tmpdir.mkdir(exist_ok=True)
    (tmpdir / CACHEDIR_TAG).touch()
    try:
        yield tmpdir
    finally:
        if not keep:
            for file in tmpdir.iterdir():
                file.unlink(missing_ok=True)
            tmpdir.rmdir()


def move_files(result: ProbeResult, target_path: Path, subdir: str) -> None:
    pinfo(Emoji.METADATA, "Moving original files")
    common = Path(commonpath(f.filename for f in result))
    if not common.is_file():
        common = result.first.filename.parent
    for file in track(result, description="Moving files", transient=True):
        file_target = target_path / subdir / file.filename.relative_to(common)
        file_target.parent.mkdir(exist_ok=True)
        shutil.move(file.filename, file_target)


def generate_output_filename(result: ProbeResult, *, avoid_transcode: bool, overwrite: bool) -> Path:
    mode, _ = result.processing_params
    ext = ".m4b"
    if mode == ProcessingMode.TRANSCODE_UNIFORM and avoid_transcode:
        ext = result.first.filename.suffix
        pinfo(Emoji.AVOIDING_TRANSCODE, f"Avoiding transcode, saving as {ext}")
    elif mode == ProcessingMode.TRANSCODE_MIXED:
        pinfo(Emoji.MUST_TRANSCODE, f"Mixed codec properties, must transcode {ext}")

    output = result.first.filename.with_name(result.first.to_filename_stem() + ext)
    if output.is_file() and not overwrite:
        pinfo(Emoji.STOP, "Target file already exists:", output.relative_to(constants.CWD), style="bold red")
        raise Exit(1)

    return output


def merge(
    concat_file: Path,
    metadata_file: Path,
    output: Path,
    total_duration: int,
    cover_file: Path | None = None,
) -> None:
    pinfo(Emoji.MERGE, "Merging to audiobook")
    args = ffmpeg.CONCAT_CMD_ARGS.copy()
    inputs: list[Path | str] = [concat_file, metadata_file]
    if cover_file:
        args += ffmpeg.CONCAT_APPEND_COVER_ADDED_ARGS
        inputs.append(cover_file)
    try:
        with Progress(transient=True) as progress:
            ffmpeg.concat(
                inputs,
                args,
                output=output,
                progress=TaskProgress.make(
                    progress,
                    total=total_duration,
                    description="Merging",
                ),
            )
    except Exception:
        output.unlink(missing_ok=True)
        raise
