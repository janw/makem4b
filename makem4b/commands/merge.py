from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import rich_click as click
from click.exceptions import Exit

from makem4b.base import process
from makem4b.cli.decorators import add_processing_options, pass_ctx_and_env
from makem4b.emoji import Emoji
from makem4b.utils import pinfo

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
    prefer_remux: bool,
    no_transcode: bool,
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
        env=env,
        files=files,
        move_originals_to=move_originals_to,
        analyze_only=analyze_only,
        prefer_remux=prefer_remux,
        no_transcode=no_transcode,
        overwrite=overwrite,
        cover=cover,
    )
