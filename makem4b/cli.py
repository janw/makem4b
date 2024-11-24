from contextlib import nullcontext
from pathlib import Path

import rich_click as click
from loguru import logger
from rich import print as rprint

from makem4b import constants, ffmpeg
from makem4b.analysis import probe_files
from makem4b.intermediates import generate_intermediates
from makem4b.metadata import extract_cover_img, generate_metadata

click.rich_click.USE_RICH_MARKUP = True
click.rich_click.USE_MARKDOWN = True


@click.command(
    context_settings={
        "auto_envvar_prefix": constants.ENVVAR_PREFIX,
    },
    help="Merge audio files into an audiobook.",
)
@click.help_option("-h", "--help")
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
    "-k",
    "--keep-intermediates",
    type=bool,
    is_flag=True,
    show_envvar=True,
)
@click.option(
    "-nt",
    "--no-transcode",
    type=bool,
    is_flag=True,
    show_envvar=True,
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
@click.option(
    "-D",
    "--debug/--no-debug",
    type=bool,
    is_flag=True,
    show_envvar=True,
)
@click.pass_context
def main(
    ctx: click.RichContext,
    files: list[Path],
    cover: Path | None,
    no_transcode: bool,  # noqa: FBT001
    keep_intermediates: bool,  # noqa: FBT001
    debug: bool,  # noqa: FBT001
) -> int:
    if debug:
        logger.enable("makem4b")
    if not files:
        click.echo(ctx.command.get_help(ctx))
        return 0

    if cover and cover.suffix.lower() not in (".png", "jpeg", ".jpg"):
        ctx.fail("Argument -c/--cover must point to JPEG or PNG file.")

    result = probe_files(files)
    extension = result.first.filename.suffix if no_transcode else ".m4b"
    output = result.files[0].filename.with_suffix(f".merged{extension}")
    with (
        generate_intermediates(result, keep=keep_intermediates, force_copy=no_transcode) as intermediates,
        generate_metadata(result, keep=keep_intermediates) as metadata_file,
        extract_cover_img(result, keep=keep_intermediates) if not cover else nullcontext(None) as extracted_cover_file,
    ):
        merge(
            intermediates,
            metadata_file=metadata_file,
            cover_file=cover or extracted_cover_file,
            total_duration=result.total_duration,
            output=output,
        )
    rprint(f'\n[b]Saved to "{output}"[/]')
    return 0


def merge(
    intermediates: list[Path],
    metadata_file: Path,
    output: Path,
    total_duration: int,
    cover_file: Path | None = None,
) -> None:
    rprint("\n[b]Merging to audiobook ... [/]")
    concat_files = "concat:" + "|".join(str(i) for i in intermediates)

    args = ffmpeg.CONCAT_CMD_ARGS.copy()
    inputs: list[Path | str] = [metadata_file, concat_files]
    if cover_file:
        args += ffmpeg.CONCAT_APPEND_COVER_ADDED_ARGS
        inputs.append(cover_file)
    try:
        ffmpeg.convert(inputs, args, output=output, total=total_duration, desc="Merging")
    except Exception:
        output.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    main.main(prog_name=constants.PROG_NAME)
