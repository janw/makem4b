from pathlib import Path

import rich_click as click
from click.exceptions import Exit
from loguru import logger

from makem4b import constants
from makem4b.analysis import print_probe_result, probe_files
from makem4b.base import generate_output_filename, handle_temp_storage, merge, move_files
from makem4b.emoji import Emoji
from makem4b.intermediates import generate_concat_file, generate_intermediates
from makem4b.metadata import extract_cover_img, generate_metadata
from makem4b.utils import copy_mtime, pinfo

click.rich_click.USE_RICH_MARKUP = True
click.rich_click.USE_MARKDOWN = True
click.rich_click.MAX_WIDTH = 140


@click.command(
    context_settings={
        "auto_envvar_prefix": constants.ENVVAR_PREFIX,
    },
)
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
    "-a",
    "--analyze-only",
    type=bool,
    is_flag=True,
    show_envvar=True,
)
@click.option(
    "-t",
    "--avoid-transcode",
    type=bool,
    is_flag=True,
    show_envvar=True,
)
@click.option(
    "-y",
    "--overwrite",
    type=bool,
    is_flag=True,
    show_envvar=True,
)
@click.option(
    "-m",
    "--move-originals-to",
    type=click.Path(
        exists=True,
        writable=True,
        file_okay=False,
        resolve_path=True,
        path_type=Path,
    ),
    default=None,
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
    "-k",
    "--keep-intermediates",
    type=bool,
    is_flag=True,
    show_envvar=True,
)
@click.option(
    "--debug/--no-debug",
    type=bool,
    is_flag=True,
    show_envvar=True,
)
@click.help_option("-h", "--help")
@click.pass_context
def main(
    ctx: click.RichContext,
    files: list[Path],
    cover: Path | None,
    move_originals_to: Path | None,
    analyze_only: bool,  # noqa: FBT001
    avoid_transcode: bool,  # noqa: FBT001
    keep_intermediates: bool,  # noqa: FBT001
    debug: bool,  # noqa: FBT001
    overwrite: bool,  # noqa: FBT001
) -> None:
    """Merge multiple audio files into an audiobook.

    MAKEM4B is a wrapper around FFmpeg that processes an arbitrary set of audio files, and turns them into an MPEG-4
    audiobook file, also known as an "M4B". MAKEM4B optimizes for quality: if the input files are already in a
    compatible format (AAC audio), they will not be transcoded (resulting in a loss of quality), but simply remuxed and
    concatenated into the final M4B.

    MAKEM4B will also attempt to populate the audiobook's metadata tags from the input files. It is somewhat opinionated
    in doing so. For example, it will only pick up metadata from the first provided file, uses the artist and album
    fields to generate the output filename, and the track and disc fields to 1 (after all, we are joining all tracks
    into a single file).

    Furthermore, the cover art embedded in the first input file is also kept if present. If the user prefers to embed a
    new/better image for this purpose, they may pass an appropriate file in using the `--cover` option.

    If the files are of mixed quality and/or codecs (for example if some are MP3s and others are M4As, or if they are
    all MP3s but with varying codec parameters such as sampling rate), they will be transcoded at the best possible
    quality given the available input. The criteria used are:

    - Highest bitrate of all input files
    - Highest sampling rate of all input files
    - Lowest channel count of all input files

    If files do not contain AAC audio but have uniform codec parameters (MP3s with the sample bit rate, sampling rate,
    channel count), the user may provide the `--avoid-transcode` flag, to have MAKEM4B produce (ironically) non-M4B
    audiobooks instead. This is the preferred option to maintain highest possible audio quality, when M4B files are not
    strictly required.
    """
    if debug:
        logger.enable("makem4b")
    if not files:
        pinfo(Emoji.NO_FILES, "No files given.", style="bold yellow")
        click.echo(ctx.command.get_help(ctx))
        raise Exit(1)

    if cover and cover.suffix.lower() not in (".png", "jpeg", ".jpg"):
        ctx.fail("Argument -c/--cover must point to JPEG or PNG file.")

    result = probe_files(files)
    if analyze_only:
        print_probe_result(result)
        raise Exit(0)

    output = generate_output_filename(result, avoid_transcode=avoid_transcode, overwrite=overwrite)

    with handle_temp_storage(result, keep=keep_intermediates) as tmpdir:
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
    pinfo(Emoji.SAVE, f'Saved to "{output.relative_to(constants.CWD)}"', style="bold green")

    if move_originals_to:
        move_files(result, target_path=move_originals_to, subdir=output.stem)


if __name__ == "__main__":
    main.main(prog_name=constants.PROG_NAME)
