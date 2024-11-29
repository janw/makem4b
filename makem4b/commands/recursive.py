from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

import rich_click as click
from click.exceptions import Exit

from makem4b.cli.decorators import add_processing_options, pass_ctx_and_env
from makem4b.commands.merge import process as merge_process
from makem4b.emoji import Emoji
from makem4b.utils import comma_separated_suffix_list, pinfo

if TYPE_CHECKING:
    from makem4b.cli.env import Environment


@click.command()
@click.help_option("-h", "--help")
@click.argument(
    "directory",
    type=click.Path(
        exists=True,
        readable=True,
        file_okay=False,
        resolve_path=True,
        path_type=Path,
    ),
)
@click.option(
    "-rt",
    "--recursive-types",
    type=comma_separated_suffix_list,
    default=[".m4a", ".mp3"],
    help="""Filename extensions to be considered.""",
    show_default=True,
)
@add_processing_options
@pass_ctx_and_env
def cli(
    ctx: click.RichContext,
    env: Environment,
    *,
    directory: Path,
    move_originals_to: Path | None,
    recursive_types: list[str],
    analyze_only: bool,
    avoid_transcode: bool,
    overwrite: bool,
) -> None:
    """Recurse into a directory to make audiobooks within its subdirectories.

    \b
    For each of the subdirectories, MAKEM4B checks for files with mergeable filename extensions
    (see `--recursive-types`), and two or more files of the same type are found, they will be merged into an audiobook
    to be placed in that directory. This option cannot be combined with passing filenames explicitly.

    Unless `--overwrite` is passed as well, MAKEM4B will attempt to act in an idempotent manner: if a given directory
    already contains a file with the prospective output filename, it will skip the directory.
    """
    suffixes = "|".join(re.escape(suff) for suff in recursive_types)
    re_types = re.compile(rf"^.+({suffixes})$")

    if not directory:
        pinfo(Emoji.NO_FILES, "No files given.", style="bold yellow")
        click.echo(ctx.command.get_help(ctx))
        raise Exit(2)

    for dirpath, _, filenames in directory.walk():
        matches = filter_files(dirpath=dirpath, filenames=filenames, regex=re_types)

        seen_types = list(matches.keys())
        if (type_cnt := len(seen_types)) > 1:
            pinfo(
                Emoji.STOP,
                f"Skipping directory, multiple filetypes ({type_cnt}): {dirpath.relative_to(directory)}",
            )
            continue
        elif type_cnt < 1:
            continue

        seen_files = sorted(matches[seen_types[0]])
        if len(seen_files) < 2:
            pinfo(
                Emoji.STOP,
                f"Skipping directory, fewer than 2 matching files: {dirpath.relative_to(directory)}",
            )
            continue

        try:
            pinfo(Emoji.INFO, f"Processing {dirpath.relative_to(env.cwd)}")
            merge_process(
                ctx=ctx,
                env=env,
                files=seen_files,
                move_originals_to=move_originals_to,
                analyze_only=analyze_only,
                avoid_transcode=avoid_transcode,
                overwrite=overwrite,
            )
        except Exit:
            pass


def filter_files(dirpath: Path, filenames: list[str], regex: re.Pattern) -> dict[str, list[Path]]:
    matches: dict[str, list[Path]] = defaultdict(list)
    for filen in filenames:
        if regex.match(filen):
            filepath = dirpath / filen
            matches[filepath.suffix].append(filepath)
    return dict(matches)