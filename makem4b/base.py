from os.path import commonpath
from pathlib import Path

from click.exceptions import Exit
from rich.progress import Progress
from tqdm import tqdm

from makem4b import constants, ffmpeg
from makem4b.emoji import Emoji
from makem4b.models import ProbeResult, ProcessingMode
from makem4b.utils import TaskProgress, pinfo


def move_files(result: ProbeResult, target_path: Path, subdir: str) -> None:
    pinfo(Emoji.METADATA, "Moving original files")
    common = Path(commonpath(f.filename for f in result))
    if not common.is_file():
        common = result.first.filename.parent
    for file in tqdm(result, desc="Moving files", leave=False, miniters=1):
        file_target = target_path / subdir / file.filename.relative_to(common)
        file_target.parent.mkdir(exist_ok=True)
        file.filename.replace(file_target)


def generate_output_filename(result: ProbeResult, *, avoid_transcode: bool, overwrite: bool) -> Path:
    mode, _ = result.processing_params
    ext = ".m4b"
    if mode == ProcessingMode.TRANSCODE_UNIFORM and avoid_transcode:
        ext = result.first.filename.suffix
        pinfo(Emoji.AVOIDING_TRANSCODE, f"Avoiding transcode, saving as {ext}")
    elif mode == ProcessingMode.TRANSCODE_MIXED:
        pinfo(Emoji.MUST_TRANSCODE, f"Mixed codec properties, must transcode {ext}")

    output = result.first.filename.with_name(result.first.metadata.to_filename_stem() + ext)
    if output.is_file() and not overwrite:
        pinfo(Emoji.STOP, "Target file already exists:", output.relative_to(constants.CWD), style="bold red")
        raise Exit(1)

    return output


def merge(
    intermediates: list[Path],
    metadata_file: Path,
    output: Path,
    total_duration: int,
    cover_file: Path | None = None,
) -> None:
    pinfo(Emoji.MERGE, "Merging to audiobook")
    concat_files = "concat:" + "|".join(str(i) for i in intermediates)

    args = ffmpeg.CONCAT_CMD_ARGS.copy()
    inputs: list[Path | str] = [metadata_file, concat_files]
    if cover_file:
        args += ffmpeg.CONCAT_APPEND_COVER_ADDED_ARGS
        inputs.append(cover_file)
    try:
        with Progress(transient=True) as progress:
            ffmpeg.convert(
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
