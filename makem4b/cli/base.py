from __future__ import annotations

import pkgutil
from typing import TYPE_CHECKING

import rich_click as click
from loguru import logger

from makem4b import commands, constants
from makem4b.cli import options
from makem4b.cli.decorators import pass_ctx_and_env

if TYPE_CHECKING:
    from makem4b.cli.env import Environment

help_config = click.RichHelpConfiguration(
    style_helptext_first_line="bold",
    style_helptext="",
    style_required_short="bold red",
    style_required_long="bold dim red",
    max_width=140,
    text_markup="markdown",
    option_groups={
        "*": [
            {
                "name": "Common processing options",
                "options": options.PROCESSING_OPTION_NAMES,
            },
            {
                "name": "Debugging options",
                "options": ["-k", "-D"],
            },
            {
                "name": "Misc options",
                "options": [
                    "--help",
                ],
            },
        ]
    },
)


class NamedCommandsCli(click.RichGroup):
    def list_commands(self, ctx: click.Context) -> list[str]:
        return sorted(mod.name for mod in pkgutil.iter_modules(commands.__path__) if mod.name != "base")

    def get_command(self, ctx: click.Context, name: str) -> click.RichCommand:
        return __import__(f"makem4b.commands.{name}", None, None, ["cli"]).cli


@click.command(
    cls=NamedCommandsCli,
    context_settings={
        "auto_envvar_prefix": constants.ENVVAR_PREFIX,
    },
)
@click.help_option("-h", "--help")
@click.rich_config(help_config)
@click.option(
    "-k",
    "--keep-intermediates",
    type=bool,
    is_flag=True,
    show_envvar=True,
)
@click.option(
    "-D",
    "--debug",
    type=bool,
    is_flag=True,
    show_envvar=True,
)
@pass_ctx_and_env
def main(
    ctx: click.RichContext,
    env: Environment,
    *,
    debug: bool,
    keep_intermediates: bool,
) -> None:
    """Merge multiple audio files into an audiobook.

    \b
    MAKEM4B is a wrapper around FFmpeg that processes an arbitrary set of audio files, and turns them into an MPEG-4
    audiobook file, also known as an "M4B". MAKEM4B optimizes for quality: if the input files are already in a
    compatible format (AAC audio), they will not be transcoded (resulting in a loss of quality), but simply remuxed and
    concatenated into the final M4B.

    \b
    MAKEM4B will also attempt to populate the audiobook's metadata tags from the input files. It is somewhat opinionated
    in doing so. For example, it will only pick up metadata from the first provided file, uses the artist and album
    fields to generate the output filename, and the track and disc fields to 1 (after all, we are joining all tracks
    into a single file).

    \b
    Furthermore, the cover art embedded in the first input file is also kept if present. If the user prefers to embed a
    new/better image for this purpose, they may pass an appropriate file in using the `--cover` option.

    \b
    If the files are of mixed quality and/or codecs (for example if some are MP3s and others are M4As, or if they are
    all MP3s but with varying codec parameters such as sampling rate), they will be transcoded at the best possible
    quality given the available input. The criteria used are:

    \b
    - Highest bitrate of all input files
    - Highest sampling rate of all input files
    - Lowest channel count of all input files

    \b
    If files do not contain AAC audio but have uniform codec parameters (MP3s with the sample bit rate, sampling rate,
    channel count), the user may provide the `--avoid-transcode` flag, to have MAKEM4B produce (ironically) non-M4B
    audiobooks instead. This is the preferred option to maintain highest possible audio quality, when M4B files are not
    strictly required.
    """
    env.debug = debug
    env.keep_intermediates = keep_intermediates

    if debug:
        logger.enable("makem4b")
