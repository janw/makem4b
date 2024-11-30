from __future__ import annotations

import shutil
from os.path import commonpath
from pathlib import Path
from typing import TYPE_CHECKING

from click.exceptions import Exit
from rich.progress import Progress, track

from makem4b import constants, ffmpeg
from makem4b.analysis import print_probe_result, probe_files
from makem4b.emoji import Emoji
from makem4b.intermediates import generate_concat_file, generate_intermediates
from makem4b.metadata import extract_cover_img, generate_metadata
from makem4b.types import ProbeResult, ProcessingMode
from makem4b.utils import TaskProgress, pinfo

if TYPE_CHECKING:
    from makem4b.cli.env import Environment

CACHEDIR_TAG = "CACHEDIR.TAG"


def move_files(result: ProbeResult, target_path: Path, subdir: str) -> None:
    pinfo(Emoji.METADATA, "Moving original files")
    common = Path(commonpath(f.filename for f in result))
    if not common.is_file():
        common = result.first.filename.parent
    for file in track(result, description="Moving files", transient=True):
        file_target = target_path / subdir / file.filename.relative_to(common)
        file_target.parent.mkdir(exist_ok=True)
        shutil.move(file.filename, file_target)


def generate_output_filename(result: ProbeResult, *, prefer_remux: bool, overwrite: bool) -> Path:
    mode, _ = result.processing_params
    ext = ".m4b"
    if mode == ProcessingMode.TRANSCODE_UNIFORM and prefer_remux:
        ext = result.first.filename.suffix
        pinfo(Emoji.AVOIDING_TRANSCODE, f"Avoiding transcode, saving as {ext}")
    elif mode == ProcessingMode.TRANSCODE_MIXED:
        pinfo(Emoji.MUST_TRANSCODE, f"Mixed codec properties, must transcode {ext}")

    output = result.first.filename.with_name(result.first.output_filename_stem + ext).resolve()
    if output.is_file() and not overwrite:
        pinfo(Emoji.STOP, "Target file already exists:", output.relative_to(constants.CWD), style="bold red")
        raise Exit(1)

    return output


def merge(
    concat_file: Path,
    *,
    metadata_file: Path,
    output: Path,
    total: int,
    cover_file: Path | None = None,
    disable_progress: bool = False,
) -> None:
    pinfo(Emoji.MERGE, "Merging to audiobook")
    args = ffmpeg.CONCAT_CMD_ARGS.copy()
    inputs: list[Path | str] = [concat_file, metadata_file]
    if cover_file:
        args += ffmpeg.CONCAT_APPEND_COVER_ADDED_ARGS
        inputs.append(cover_file)
    try:
        with Progress(transient=True, disable=disable_progress) as progress:
            ffmpeg.concat(
                inputs,
                args,
                output=output,
                progress=TaskProgress.make(
                    progress,
                    total=total,
                    description="Merging",
                ),
            )
    except Exception:
        output.unlink(missing_ok=True)
        raise


def process(
    env: Environment,
    *,
    files: list[Path],
    move_originals_to: Path | None,
    analyze_only: bool,
    prefer_remux: bool,
    no_transcode: bool,
    overwrite: bool,
    cover: Path | None = None,
) -> None:
    result = probe_files(files, disable_progress=env.debug)
    if analyze_only:
        print_probe_result(result)
        raise Exit(0)

    if no_transcode and result.processing_params[0] == ProcessingMode.TRANSCODE_MIXED:
        pinfo(Emoji.STOP, "Files require transcode. Bailing.")
        raise Exit(8)

    output = generate_output_filename(result, prefer_remux=prefer_remux, overwrite=overwrite)

    with env.handle_temp_storage(parent=files[0].parent) as tmpdir:
        intermediates, durations = generate_intermediates(
            result,
            tmpdir=tmpdir,
            prefer_remux=prefer_remux,
            disable_progress=env.debug,
        )
        concat_file = generate_concat_file(
            intermediates,
            tmpdir=tmpdir,
        )
        metadata_file = generate_metadata(
            result.files,
            durations=durations,
            tmpdir=tmpdir,
        )
        cover_file = cover or extract_cover_img(
            result,
            tmpdir=tmpdir,
        )

        merge(
            concat_file,
            metadata_file=metadata_file,
            cover_file=cover_file,
            total=result.approx_size,
            output=output,
            disable_progress=env.debug,
        )

    # copy_mtime(result.first.filename, output)
    pinfo(Emoji.SAVE, f'Saved to "{output.relative_to(env.cwd)}"\n', style="bold green")

    if move_originals_to:
        move_files(result, target_path=move_originals_to, subdir=output.stem)
