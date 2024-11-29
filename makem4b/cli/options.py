from pathlib import Path

import rich_click as click

PROCESSING_OPTIONS: list[click.Parameter] = [
    click.Option(
        [
            "-a",
            "--analyze-only",
        ],
        type=bool,
        is_flag=True,
        show_envvar=True,
        help="""
            Analyze the input files and emit a report about their audio properties,
            including the format of a prospective audiobook resulting from them. No
            actual processing will be attempted.
        """,
    ),
    click.Option(
        [
            "-t",
            "--avoid-transcode",
        ],
        type=bool,
        is_flag=True,
        show_envvar=True,
        help="""
            Avoid transcoding the input files to create the audiobook. MAKEM4B will not
            attempt to convert the files to produce the audiobook but instead use them
            as-is and simply concatenate them in their original format. Since no
            conversion will take place this option will preserve the full quality of the
            input material. **Requires all files to be using the same format** (codec,
            sample rate, bit rate, and number of channels).
        """,
    ),
    click.Option(
        [
            "-m",
            "--move-originals-to",
        ],
        type=click.Path(
            exists=True,
            writable=True,
            file_okay=False,
            resolve_path=True,
            path_type=Path,
        ),
        default=None,
        show_envvar=True,
        help="""
            Move the input files to the given directory upon successful creation of the
            audiobook. MAKEM4B will create a subdirectory of the same name as the parent
            directory of the input files, allowing users to create an "archive" of the
            original files of their collection.
        """,
    ),
    click.Option(
        [
            "-y",
            "--overwrite",
        ],
        type=bool,
        is_flag=True,
        show_envvar=True,
        help="""Overwrite the output file if it already exists""",
    ),
]

PROCESSING_OPTION_NAMES = [o.opts[0] for o in PROCESSING_OPTIONS]
