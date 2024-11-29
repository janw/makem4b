from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import rich_click as click
from click.exceptions import Exit

from makem4b.analysis import print_probe_result, probe_files
from makem4b.base import generate_output_filename, handle_temp_storage, merge, move_files
from makem4b.cli.decorators import add_processing_options, pass_ctx_and_env
from makem4b.emoji import Emoji
from makem4b.intermediates import generate_concat_file, generate_intermediates
from makem4b.metadata import extract_cover_img, generate_metadata
from makem4b.utils import copy_mtime, pinfo

if TYPE_CHECKING:
    from makem4b.cli.env import Environment


@click.command()
@click.help_option("-h", "--help")
@add_processing_options
@click.argument(
    "files",
    nargs=-1,
    type=click.Path(
        exists=True,
        readable=True,
        dir_okay=False,
        resolve_path=True,
        path_type=Path,
    ),
)
@click.option(
    "-c",
    "--cover",
    type=click.Path(
        exists=True,
        readable=True,
        dir_okay=False,
        resolve_path=True,
        path_type=Path,
    ),
    default=None,
)
@pass_ctx_and_env
def cli(
    ctx: click.RichContext,
    env: Environment,
    *,
    files: list[Path],
    move_originals_to: Path | None,
    analyze_only: bool,
    avoid_transcode: bool,
    overwrite: bool,
    cover: Path | None,
) -> None:
    """Merge multiple audio files into an audiobook."""
    if not files:
        pinfo(Emoji.NO_FILES, "No files given.", style="bold yellow")
        click.echo(ctx.command.get_help(ctx))
        raise Exit(1)

    if cover and cover.suffix.lower() not in (".png", "jpeg", ".jpg"):
        ctx.fail("Argument -c/--cover must point to JPEG or PNG file.")

    process(
        ctx=ctx,
        env=env,
        files=files,
        move_originals_to=move_originals_to,
        analyze_only=analyze_only,
        avoid_transcode=avoid_transcode,
        overwrite=overwrite,
        cover=cover,
    )


def process(
    ctx: click.RichContext,
    env: Environment,
    *,
    files: list[Path],
    move_originals_to: Path | None,
    analyze_only: bool,
    avoid_transcode: bool,
    overwrite: bool,
    cover: Path | None = None,
) -> None:
    result = probe_files(files)
    if analyze_only:
        print_probe_result(result)
        raise Exit(0)

    output = generate_output_filename(result, avoid_transcode=avoid_transcode, overwrite=overwrite)

    with handle_temp_storage(result, keep=env.keep_intermediates) as tmpdir:
        intermediates = generate_intermediates(result, tmpdir=tmpdir, avoid_transcode=avoid_transcode)
        concat_file = generate_concat_file(intermediates, tmpdir=tmpdir)
        metadata_file = generate_metadata(result, tmpdir=tmpdir)
        cover_file = cover or extract_cover_img(result, tmpdir=tmpdir)

        merge(
            concat_file,
            metadata_file=metadata_file,
            cover_file=cover_file,
            total_duration=result.total_duration,
            output=output,
        )

    copy_mtime(result.first.filename, output)
    pinfo(Emoji.SAVE, f'Saved to "{output.relative_to(env.cwd)}"\n', style="bold green")

    if move_originals_to:
        move_files(result, target_path=move_originals_to, subdir=output.stem)
